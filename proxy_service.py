import os
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

async def forward_to_groq(request_body: dict) -> dict:
    """
    Forwards the chat completion request to the Groq API.
    """
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="GROQ_API_KEY is not configured in the environment."
        )
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # We append /chat/completions in case the base URL doesn't include it. 
    # If the user passed the full path in GROQ_BASE_URL, we'll need to adjust, 
    # but normally base url is just the domain or version path.
    url = f"{GROQ_BASE_URL}/chat/completions"
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
