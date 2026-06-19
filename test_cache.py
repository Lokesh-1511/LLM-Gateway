import httpx
import asyncio
import time

async def run_request(client, prompt: str):
    url = "http://localhost:8000/v1/chat/completions"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    start_time = time.time()
    response = await client.post(url, json=payload, timeout=None)
    elapsed_time = time.time() - start_time
    
    print(f"--- Prompt: '{prompt}' ---")
    print(f"Status: {response.status_code}")
    print(f"Time Taken: {elapsed_time:.3f} seconds")
    
    # We only print the text response to keep the output clean
    if response.status_code == 200:
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            print(f"Response: {data['choices'][0]['message']['content'].strip()}")
    print("\n")


async def test_semantic_cache():
    async with httpx.AsyncClient() as client:
        # First Run: Ask a question
        print(">>> 1. FIRST RUN (Should call Groq, takes 0.5s - 1.0s) <<<")
        await run_request(client, "Tell me a joke about a cat.")
        
        # Give the background task a tiny bit of time to save the cache
        await asyncio.sleep(0.5)

        # Second Run: Exact same question
        print(">>> 2. SECOND RUN (Exact match, should return instantly) <<<")
        await run_request(client, "Tell me a joke about a cat.")
        
        # Third Run: Semantic Test (Different words, same meaning)
        print(">>> 3. SEMANTIC TEST (Different words, should also return instantly) <<<")
        await run_request(client, "Can you give me a joke about a feline?")

if __name__ == "__main__":
    asyncio.run(test_semantic_cache())

