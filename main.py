from fastapi import FastAPI, Request, HTTPException
from proxy_service import forward_to_groq
from security_service import PIIFirewall

app = FastAPI(
    title="PromptOps Gateway",
    description="Enterprise LLM Gateway Pass-Through Proxy",
    version="1.0.0"
)

# Initialize the PII Firewall once when the app starts
firewall = PIIFirewall()

@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
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
    if "messages" in body and isinstance(body["messages"], list):
        for message in body["messages"]:
            if "content" in message and isinstance(message["content"], str):
                original_content = message["content"]
                # Pass the user's prompt through the firewall
                scrubbed_content = firewall.scrub_text(original_content)
                message["content"] = scrubbed_content
    # ---------------------------------
    
    # Forward the parsed (and now scrubbed) JSON to our proxy service
    response = await forward_to_groq(body)
    
    # Return the target LLM API's response back to the client
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
