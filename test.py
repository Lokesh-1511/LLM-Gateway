import httpx
import asyncio

async def test_gateway():
    url = "http://localhost:8000/v1/chat/completions"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "My name is John Doe and my email is john.doe@example.com. Tell me a joke."}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=None)
        print("Status:", response.status_code)
        print("Response:", response.json())

asyncio.run(test_gateway())
