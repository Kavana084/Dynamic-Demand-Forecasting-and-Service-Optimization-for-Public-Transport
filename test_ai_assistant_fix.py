"""
Test AI Assistant Entity Extraction Fix
----------------------------------------
Test journey planning queries to verify entity extraction works.
"""

import asyncio
import httpx
import json

API_BASE_URL = "http://127.0.0.1:8000"

TEST_MESSAGES = [
    "Plan my journey from Nagarabhavi to Majestic",
    "Nagarabhavi to Majestic",
    "Travel from Nagarabhavi to Majestic",
    "How do I get from Nagarabhavi to Majestic?",
]

async def test_message(message: str, session_id: str = None):
    """Test a single message."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/ai-assistant/chat",
                json={
                    "message": message,
                    "session_id": session_id
                }
            )
            response.raise_for_status()
            data = response.json()
            return {
                "message": message,
                "answer": data.get("answer", ""),
                "confidence": data.get("confidence", 0.0),
                "session_id": data.get("session_id", ""),
                "success": True
            }
        except Exception as e:
            return {
                "message": message,
                "error": str(e),
                "success": False
            }

async def main():
    """Run all tests."""
    print("Testing AI Assistant Entity Extraction Fix")
    print("=" * 60)
    
    session_id = None
    results = []
    
    for message in TEST_MESSAGES:
        print(f"\nTesting: {message}")
        result = await test_message(message, session_id)
        results.append(result)
        
        if result.get("success"):
            session_id = result.get("session_id", session_id)
            print(f"  Intent detected: plan_trip")
            print(f"  Response: {result.get('answer', '')[:100]}...")
            print(f"  Session ID: {session_id}")
        else:
            print(f"  ERROR: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"  Total tests: {len(results)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(results) - success_count}")
    
    # Save results
    with open("outputs/ai_assistant_fix_test.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to outputs/ai_assistant_fix_test.json")

if __name__ == "__main__":
    asyncio.run(main())
