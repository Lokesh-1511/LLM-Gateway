import httpx
import asyncio

async def test_gateway():
    # 1. Login to get token
    auth_url = "http://127.0.0.1:8000/api/auth/login"
    auth_data = {
        "username": "admin@promptops.local",
        "password": "admin123"
    }
    
    async with httpx.AsyncClient() as client:
        print("Logging in...")
        auth_response = await client.post(auth_url, data=auth_data)
        if auth_response.status_code != 200:
            print("Failed to login:", auth_response.text)
            return
            
        token = auth_response.json().get("access_token")
        print("Login successful! Token acquired.")
        
        # 2. Test Chat Completions with PII
        chat_url = "http://127.0.0.1:8000/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "My name is John Doe , i want to send my mail to Mary and my email is john.doe@example.com. mary mail is mary2020@email.com .Say hello to me using my name and mention my email."}]
        }
        
        print("\nSending request with PII...")
        response = await client.post(chat_url, headers=headers, json=payload, timeout=None)
        
        print("Status:", response.status_code)
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                print("\nResponse from LLM:")
                print(data["choices"][0]["message"]["content"])
        else:
            print("Error:", response.text)

if __name__ == "__main__":
    asyncio.run(test_gateway())
