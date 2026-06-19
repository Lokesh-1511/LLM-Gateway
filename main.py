import time
import tiktoken
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from proxy_service import forward_to_groq
from security_service import PIIFirewall
from cache_service import SemanticCache
from database import log_request, SessionLocal, RequestLog
from sqlalchemy import func

app = FastAPI(
    title="PromptOps Gateway",
    description="Enterprise LLM Gateway Pass-Through Proxy",
    version="1.0.0"
)

# Enable CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the PII Firewall once when the app starts
firewall = PIIFirewall()
# Initialize the Semantic Cache
cache = SemanticCache()

@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request, background_tasks: BackgroundTasks):
    """
    Intercepts POST requests to /v1/chat/completions and proxies them to the target LLM API.
    """
    try:
        # Parse the incoming JSON body
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    start_time = time.time()
    
    # --- PHASE 2: SECURITY MODULE ---
    # Intercept the messages and scrub PII before forwarding
    full_prompt = ""
    any_pii_detected = False
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                original_content = message["content"]
                # Pass the user's prompt through the firewall
                scrubbed_content, pii_detected = await run_in_threadpool(firewall.scrub_text, original_content)
                message["content"] = scrubbed_content
                any_pii_detected = any_pii_detected or pii_detected
                # Concatenate all messages into a single prompt string for caching
                full_prompt += scrubbed_content + "\n"
    
    full_prompt = full_prompt.strip()
    # ---------------------------------
    
    # --- PHASE 3: SEMANTIC CACHE ---
    # Check if we have a semantically similar prompt already cached
    cached_response = await run_in_threadpool(cache.query_cache, full_prompt)
    if cached_response:
        latency_ms = (time.time() - start_time) * 1000
        
        # Estimate tokens since we bypassed Groq
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            cached_content = cached_response["choices"][0]["message"]["content"]
            token_count = len(encoding.encode(full_prompt)) + len(encoding.encode(cached_content))
        except Exception:
            token_count = 0
            
        # Log to Database
        background_tasks.add_task(
            log_request,
            original_prompt=full_prompt,
            was_pii_detected=any_pii_detected,
            was_cache_hit=True,
            token_count=token_count,
            latency_ms=latency_ms,
            estimated_cost=0.0 # Cache hits cost us nothing
        )
        return cached_response
    # ---------------------------------
    
    # Forward the parsed (and now scrubbed) JSON to our proxy service
    response = await forward_to_groq(body)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Extract total tokens from Groq response
    token_count = 0
    if "usage" in response and "total_tokens" in response["usage"]:
        token_count = response["usage"]["total_tokens"]
        
    estimated_cost = token_count * 0.000002
    
    # --- PHASE 4: ADD TO DB ---
    background_tasks.add_task(
        log_request,
        original_prompt=full_prompt,
        was_pii_detected=any_pii_detected,
        was_cache_hit=False,
        token_count=token_count,
        latency_ms=latency_ms,
        estimated_cost=estimated_cost
    )
    
    # --- PHASE 3: ADD TO CACHE ---
    # Save the sanitized prompt and the response to the cache in the background
    background_tasks.add_task(cache.add_to_cache, full_prompt, response)
    # ---------------------------------
    
    # Return the target LLM API's response back to the client
    return response

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """
    Returns aggregated analytics from the database.
    """
    db = SessionLocal()
    try:
        total_requests = db.query(RequestLog).count()
        total_pii_blocked = db.query(RequestLog).filter(RequestLog.was_pii_detected == True).count()
        
        tokens_saved = db.query(func.sum(RequestLog.token_count)).filter(RequestLog.was_cache_hit == True).scalar()
        if tokens_saved is None:
            tokens_saved = 0
            
        total_savings = tokens_saved * 0.000002
        
        recent_logs_query = db.query(RequestLog).order_by(RequestLog.timestamp.desc()).limit(10).all()
        recent_logs = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "original_prompt": log.original_prompt,
                "was_pii_detected": log.was_pii_detected,
                "was_cache_hit": log.was_cache_hit,
                "token_count": log.token_count,
                "latency_ms": log.latency_ms,
                "estimated_cost": log.estimated_cost
            }
            for log in recent_logs_query
        ]
        
        return {
            "total_requests": total_requests,
            "total_pii_blocked": total_pii_blocked,
            "total_savings": total_savings,
            "recent_logs": recent_logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
