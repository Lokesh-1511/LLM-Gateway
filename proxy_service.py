import os
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

async def forward_to_provider(request_body: dict, api_key: str, base_url: str, target_model: str = None) -> dict:
    """
    Forwards the chat completion request to the dynamic upstream API.
    """
    if target_model:
        request_body["model"] = target_model
        
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="API Key is missing for this model."
        )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{base_url}/chat/completions"
    if url.endswith("/chat/completions/chat/completions"):
        url = url.replace("/chat/completions/chat/completions", "/chat/completions")
    
    async with httpx.AsyncClient() as client:
        try:
            # Forward the request body exactly as received
            response = await client.post(url, json=request_body, headers=headers)
            # Raise an exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            # Error returned by the Groq API itself (e.g., 401 Unauthorized, 429 Rate Limit)
            try:
                error_detail = e.response.json()
            except ValueError:
                error_detail = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            
        except httpx.RequestError as e:
            # Network-level error (e.g., DNS failure, connection timeout)
            raise HTTPException(status_code=503, detail=f"Failed to connect to Groq API: {str(e)}")
