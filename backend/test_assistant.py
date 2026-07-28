import asyncio
import httpx
import time
import uuid

async def test_assistant():
    url = "http://localhost:8000/api/ai-assistant/chat"
    session_id = str(uuid.uuid4())
    
    print(f"Testing session: {session_id}")
    
    # 1. Test Context & Response
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"message": "What is route 500-D?", "session_id": session_id}, timeout=30.0)
            data = resp.json()
            print(f"Query 1 Response time: {time.time() - start:.2f}s")
            print(f"Response: {data.get('answer')}")
            
            # 2. Test Follow-up (Context)
            start = time.time()
            resp = await client.post(url, json={"message": "How crowded is it?", "session_id": session_id}, timeout=30.0)
            data = resp.json()
            print(f"Query 2 (Follow-up) Response time: {time.time() - start:.2f}s")
            print(f"Response: {data.get('answer')}")
            
    except Exception as e:
        print(f"Connection error. Make sure the backend is running: {e}")

if __name__ == "__main__":
    asyncio.run(test_assistant())
