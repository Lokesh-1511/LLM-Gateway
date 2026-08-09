import asyncio
import httpx

async def test_chat_title():
    async with httpx.AsyncClient() as client:
        # 1. Login
        auth = await client.post("http://127.0.0.1:8000/api/auth/login", data={
            "username": "admin@promptops.local",
            "password": "admin123"
        })
        token = auth.json()["access_token"]
        
        # 2. Send first message without a chat-id (so it creates one)
        headers = {
            "Authorization": f"Bearer {token}",
            "x-model-target": "Fast (8B)"
        }
        body = {
            "messages": [{"role": "user", "content": "Tell me a joke about a very fast turtle."}]
        }
        print("Sending message...")
        res = await client.post("http://127.0.0.1:8000/v1/chat/completions", json=body, headers=headers)
        chat_id = res.headers.get("x-chat-id")
        print(f"Got chat ID: {chat_id}")
        
        # Wait a couple seconds for background task
        await asyncio.sleep(3)
        
        # 3. Check chats list to see if title updated
        chats_res = await client.get("http://127.0.0.1:8000/api/chats", headers=headers)
        chats = chats_res.json()
        new_chat = next((c for c in chats if c["id"] == chat_id), None)
        print(f"Chat Title is: {new_chat['title']}")

if __name__ == "__main__":
    asyncio.run(test_chat_title())
