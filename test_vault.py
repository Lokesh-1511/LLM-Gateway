import httpx
import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal
from models import PIIMapping

async def test_identity_vault():
    auth_url = "http://127.0.0.1:8000/api/auth/login"
    chat_url = "http://127.0.0.1:8000/v1/chat/completions"
    
    auth_data = {
        "username": "admin@promptops.local",
        "password": "admin123"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("Logging in...")
        auth_response = await client.post(auth_url, data=auth_data)
        if auth_response.status_code != 200:
            print("Failed to login:", auth_response.text)
            return
            
        token = auth_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Turn 1: Send message with PII and generate a new chat
        print("\n--- TURN 1 ---")
        payload_1 = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "My name is Alice Smith and my phone number is 555-0100. Please remember this."}]
        }
        
        print("Sending initial message...")
        resp_1 = await client.post(chat_url, headers=headers, json=payload_1, timeout=60.0)
        
        if resp_1.status_code != 200:
            print("Error:", resp_1.text)
            return
            
        chat_id = resp_1.headers.get("x-chat-id")
        print(f"Server created new Chat ID: {chat_id}")
        print("Response 1:", resp_1.json()["choices"][0]["message"]["content"])
        
        # 3. Turn 2: Send a follow-up message in the SAME chat using the SAME PII
        print("\n--- TURN 2 ---")
        headers["x-chat-id"] = chat_id
        payload_2 = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "user", "content": "What is my name and phone number? And also email me at alice.smith@example.com"}
            ]
        }
        
        print(f"Sending follow-up message using Chat ID: {chat_id}...")
        resp_2 = await client.post(chat_url, headers=headers, json=payload_2, timeout=60.0)
        print("Response 2:", resp_2.json()["choices"][0]["message"]["content"])
        
        # 4. Verify Database Records
        print("\n--- VERIFYING IDENTITY VAULT (DB) ---")
        db: Session = SessionLocal()
        try:
            mappings = db.query(PIIMapping).filter(PIIMapping.chat_id == chat_id).all()
            print(f"Found {len(mappings)} PII mappings in the vault for this chat:")
            for m in mappings:
                print(f"  - Real: '{m.real_value}' -> Fake: '{m.fake_value}'")
        finally:
            db.close()

if __name__ == "__main__":
    asyncio.run(test_identity_vault())
