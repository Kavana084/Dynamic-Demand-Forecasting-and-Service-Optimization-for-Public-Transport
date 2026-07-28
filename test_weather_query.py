"""
Test Weather Query Debug
-------------------------
Test the AI Assistant with a weather query to trace the execution path.
"""

import asyncio
import httpx
import json

API_BASE_URL = "http://127.0.0.1:8000"

async def test_weather_query():
    """Test a weather query."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # First, plan a trip to establish context
            print("Step 1: Planning a trip to establish context...")
            trip_response = await client.post(
                f"{API_BASE_URL}/api/ai-assistant/chat",
                json={
                    "message": "Plan a trip from Nagarabhavi to Majestic",
                    "session_id": None
                }
            )
            trip_response.raise_for_status()
            trip_data = trip_response.json()
            session_id = trip_data.get("session_id")
            print(f"  Trip planned. Session ID: {session_id}")
            print(f"  Response: {trip_data.get('answer', '')[:100]}...")
            
            # Now ask about weather
            print("\nStep 2: Asking about weather impact...")
            weather_response = await client.post(
                f"{API_BASE_URL}/api/ai-assistant/chat",
                json={
                    "message": "Will rain affect my trip?",
                    "session_id": session_id
                }
            )
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            print(f"  Weather query response received")
            print(f"  Answer: {weather_data.get('answer', '')}")
            print(f"  Confidence: {weather_data.get('confidence', 0.0)}")
            
            return {
                "trip_response": trip_data,
                "weather_response": weather_data,
                "session_id": session_id
            }
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e)
            }

if __name__ == "__main__":
    result = asyncio.run(test_weather_query())
    
    with open("outputs/weather_query_debug.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("\nResults saved to outputs/weather_query_debug.json")
