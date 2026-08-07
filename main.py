import time
import tiktoken
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

import copy
from proxy_service import forward_to_groq
from security_service import StatefulPIIFirewall
from cache_service import SemanticCache, PolicyGuardrail
from database import log_request, SessionLocal
from routing_service import RoutingEngine
from models import RequestLog, User, Chat, Message, Department
from auth_service import get_current_user, get_db, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
from pydantic import BaseModel
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
firewall = StatefulPIIFirewall()
# Initialize the Semantic Cache
cache = SemanticCache()
# Initialize the Policy Guardrail
guardrail = PolicyGuardrail()
# Initialize the Routing Engine
routing_engine = RoutingEngine()

@app.post("/api/auth/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "department_id": user.department_id, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class SignupRequest(BaseModel):
    email: str
    password: str
    department_id: str

@app.get("/api/departments")
async def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@app.post("/api/auth/signup")
async def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        department_id=req.department_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.get("/api/chats")
async def get_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at.desc()).all()

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()

@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Intercepts POST requests to /v1/chat/completions and proxies them to the target LLM API.
    """
    try:
        # Parse the incoming JSON body
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    chat_id = request.headers.get("x-chat-id")
    target_tier = request.headers.get("x-model-target", "Fast (8B)")
    
    if not chat_id or chat_id == "null":
        new_chat = Chat(user_id=current_user.id, title="New Chat")
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        chat_id = new_chat.id
        
    user_message = body.get("messages", [])[-1].get("content", "") if body.get("messages") else ""
    if user_message:
        db.add(Message(chat_id=chat_id, role="user", content=user_message))
        db.commit()

        
    start_time = time.time()
    
    # --- PHASE 1: POLICY GUARDRAIL ---
    if user_message:
        violation, policy_desc = await run_in_threadpool(guardrail.check_policy_violation, user_message)
        if violation:
            raise HTTPException(status_code=403, detail=f"Policy Violation: {policy_desc}")
    # ---------------------------------
    
    # --- PHASE 2: SECURITY MODULE ---
    # Intercept the messages and scrub PII before forwarding
    full_prompt = ""
    any_pii_detected = False
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                original_content = message["content"]
                # Pass the user's prompt through the firewall
                scrubbed_content, pii_detected = await run_in_threadpool(firewall.mask_pii, original_content, str(chat_id), db)
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
            estimated_cost=0.0, # Cache hits cost us nothing
            user_id=current_user.id,
            department_id=current_user.department_id,
            was_failover_used=False,
            provider="cache"
        )
        
        # Unmask the cached response before returning
        if "choices" in cached_response:
            for choice in cached_response["choices"]:
                if "message" in choice and "content" in choice["message"] and isinstance(choice["message"]["content"], str):
                    choice["message"]["content"] = firewall.unmask_response(choice["message"]["content"], str(chat_id), db)
                    
        return cached_response
    # ---------------------------------
    
    # --- PHASE 4: PREDICTIVE ROUTING & FAILOVER ---
    user_dept = "Unknown"
    if current_user.department_id:
        dept = db.query(Department).filter(Department.id == current_user.department_id).first()
        if dept:
            user_dept = dept.name
            
    target_model = routing_engine.select_model(user_dept)
    was_failover_used = (target_model == routing_engine.FALLBACK_MODEL)
    provider_used = target_model
    
    try:
        response = await forward_to_groq(body, target_model=target_model)
        latency_ms = (time.time() - start_time) * 1000
        routing_engine.record_metric(target_model, latency_ms, 200)
    except HTTPException as e:
        latency_ms = (time.time() - start_time) * 1000
        routing_engine.record_metric(target_model, latency_ms, e.status_code)
        
        if target_model == routing_engine.PRIMARY_MODEL:
            # Retry with fallback model
            target_model = routing_engine.FALLBACK_MODEL
            was_failover_used = True
            provider_used = target_model
            try:
                response = await forward_to_groq(body, target_model=target_model)
                latency_ms = (time.time() - start_time) * 1000
                routing_engine.record_metric(target_model, latency_ms, 200)
            except HTTPException as e_fallback:
                latency_ms = (time.time() - start_time) * 1000
                routing_engine.record_metric(target_model, latency_ms, e_fallback.status_code)
                raise e_fallback
        else:
            raise e
    # ---------------------------------
    
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
        estimated_cost=estimated_cost,
        user_id=current_user.id,
        department_id=current_user.department_id,
        was_failover_used=was_failover_used,
        provider=provider_used
    )
    
    # --- PHASE 3: ADD TO CACHE ---
    # Save the sanitized prompt and the response to the cache in the background
    # Deepcopy to ensure the cache stores the masked version
    background_tasks.add_task(cache.add_to_cache, full_prompt, copy.deepcopy(response))
    # ---------------------------------
    
    # --- PHASE 3: UNMASK PII ---
    # Unmask the LLM response before sending it back to the client
    unmasked_response_content = ""
    if "choices" in response:
        for choice in response["choices"]:
            if "message" in choice and "content" in choice["message"] and isinstance(choice["message"]["content"], str):
                choice["message"]["content"] = firewall.unmask_response(choice["message"]["content"], str(chat_id), db)
                unmasked_response_content += choice["message"]["content"]
    # ---------------------------------
    
    # Save the assistant's response to the database
    if unmasked_response_content:
        db.add(Message(chat_id=chat_id, role="assistant", content=unmasked_response_content))
        db.commit()
    
    # Add chat_id to the response headers so the frontend can update its URL/state
    headers = {"X-Chat-Id": str(chat_id)}
    from fastapi.responses import JSONResponse
    return JSONResponse(content=response, headers=headers)
    


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
