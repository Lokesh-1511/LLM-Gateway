import httpx
import asyncio
import time

async def run_request(client, prompt: str, token: str):
    url = "http://127.0.0.1:8000/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    start_time = time.time()
    response = await client.post(url, headers=headers, json=payload, timeout=None)
    elapsed_time = time.time() - start_time
    
    print(f"--- Prompt: '{prompt}' ---")
    print(f"Status: {response.status_code}")
    print(f"Time Taken: {elapsed_time:.3f} seconds")
    
    # We only print the text response to keep the output clean
    if response.status_code == 200:
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            print(f"Response: {data['choices'][0]['message']['content'].strip()}")
    else:
        print(f"Error: {response.text}")
    print("\n")


async def test_semantic_cache():
    auth_url = "http://127.0.0.1:8000/api/auth/login"
    auth_data = {
        "username": "admin@promptops.local",
        "password": "admin123"
    }

    async with httpx.AsyncClient() as client:
        print("Logging in to acquire token...")
        auth_response = await client.post(auth_url, data=auth_data)
        if auth_response.status_code != 200:
            print("Failed to login:", auth_response.text)
            return
        token = auth_response.json().get("access_token")
        print("Login successful!\n")

        # First Run: Ask a question
        print(">>> 1. FIRST RUN (Should call Groq, takes 0.5s - 1.0s) <<<")
        await run_request(client, "Tell me a joke about a dog.", token)
        
        # Give the background task a tiny bit of time to save the cache
        await asyncio.sleep(0.5)

        # Second Run: Exact same question
        print(">>> 2. SECOND RUN (Exact match, should return instantly) <<<")
        await run_request(client, "Tell me a joke about a dog.", token)
        
        # Third Run: Semantic Test (Different words, same meaning)
        print(">>> 3. SEMANTIC TEST (Different words, should also return instantly) <<<")
        await run_request(client, "Can you give me a joke about a canine?", token)

if __name__ == "__main__":
    asyncio.run(test_semantic_cache())

