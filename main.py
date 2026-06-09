from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from proxy_service import forward_to_groq
from security_service import PIIFirewall
from cache_service import SemanticCache

app = FastAPI(
    title="PromptOps Gateway",
    description="Enterprise LLM Gateway Pass-Through Proxy",
    version="1.0.0"
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
    
    # --- PHASE 2: SECURITY MODULE ---
    # Intercept the messages and scrub PII before forwarding
    full_prompt = ""
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                original_content = message["content"]
                # Pass the user's prompt through the firewall
                scrubbed_content = firewall.scrub_text(original_content)
                message["content"] = scrubbed_content
                # Concatenate all messages into a single prompt string for caching
                full_prompt += scrubbed_content + "\n"
    
    full_prompt = full_prompt.strip()
    # ---------------------------------
    
    # --- PHASE 3: SEMANTIC CACHE ---
    # Check if we have a semantically similar prompt already cached
    cached_response = cache.query_cache(full_prompt)
    if cached_response:
        return cached_response
    # ---------------------------------
    
    # Forward the parsed (and now scrubbed) JSON to our proxy service
    response = await forward_to_groq(body)
    
    # --- PHASE 3: ADD TO CACHE ---
    # Save the sanitized prompt and the response to the cache in the background
    background_tasks.add_task(cache.add_to_cache, full_prompt, response)
    # ---------------------------------
    
    # Return the target LLM API's response back to the client
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
