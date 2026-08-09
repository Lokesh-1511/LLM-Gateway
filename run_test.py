import httpx
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import RequestLog

async def run():
    print("1. Logging in as admin...")
    async with httpx.AsyncClient() as client:
        auth_response = await client.post("http://127.0.0.1:8000/api/auth/login", data={
            "username": "admin@promptops.local",
            "password": "admin123"
        })
        token = auth_response.json()["access_token"]
        
        print("\n2. Sending wordy prompt...")
        prompt = "Hello there! I was wondering if you could please kindly tell me what the capital of France is? Thank you so much!"
        
        response = await client.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=None
        )
        
        print("\n3. LLM Response received:")
        if response.status_code == 200:
            data = response.json()
            if "choices" in data:
                print(f"-> {data['choices'][0]['message']['content']}")
        else:
            print("Error:", response.text)
            
    # Wait a tiny bit for the background task to save to DB
    await asyncio.sleep(1)
    
    print("\n4. Checking Database for Token Savings...")
    engine = create_engine("sqlite:///./llm_logs.db", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Get the latest log
    latest_log = db.query(RequestLog).order_by(RequestLog.timestamp.desc()).first()
    if latest_log:
        print(f"Original Prompt in DB: '{latest_log.original_prompt}'")
        print(f"Original Tokens: {latest_log.original_token_count}")
        print(f"Compressed Tokens: {latest_log.compressed_token_count}")
        print(f"Tokens Saved: {latest_log.tokens_saved_by_compression}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(run())
