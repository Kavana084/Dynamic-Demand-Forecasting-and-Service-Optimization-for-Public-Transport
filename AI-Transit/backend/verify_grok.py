import asyncio
import time
import sys
import httpx

# Add the backend path to sys.path so we can import from app
sys.path.insert(0, '.')

from app.config import settings
from app.services.ai_assistant_service import ai_assistant_service

print("=== 1. Configuration ===")
api_key = getattr(settings, 'grok_api_key', '')
print(f"settings.grok_api_key exists? {bool(hasattr(settings, 'grok_api_key') and getattr(settings, 'grok_api_key'))}")
print(f"settings.grok_api_key length: {len(api_key)}")
print(f"settings.grok_model: {getattr(settings, 'grok_model', 'Not Configured')}")
print(f"settings.grok_api_url: {getattr(settings, 'grok_api_url', 'Not Configured')}")

print("\n=== 2. Real HTTP Request Setup ===")
# Capture the outbound request inside the actual method by wrapping it
original_post = httpx.AsyncClient.post

async def tracing_post(self, url, **kwargs):
    print(f"\n[OUTBOUND HTTP POST]")
    print(f"URL: {url}")
    json_data = kwargs.get('json', {})
    print(f"Model name: {json_data.get('model', 'Unknown')}")
    
    response = await original_post(self, url, **kwargs)
    print(f"HTTP status code: {response.status_code}")
    return response

httpx.AsyncClient.post = tracing_post

async def main():
    print("\n=== 4. Test 1: Quantum Computing ===")
    session_id = "test-session-1"
    query = "Explain quantum computing in one paragraph"
    print(f"Sending: '{query}'")
    
    intent_result = await ai_assistant_service.detect_intent(query, session_id)
    print("Intent detected:", intent_result.get('intent'))
    
    tool_call = await ai_assistant_service.execute_tool(
        intent=intent_result.get('intent'),
        parameters=intent_result.get('parameters', {}),
        session_id=session_id
    )
    print("Tool selected:", tool_call.tool_name)
    
    final_response = await ai_assistant_service.format_response(tool_call, query)
    print("Final response:", final_response)


    print("\n=== 5. Test 2: Journey Planning ===")
    session_id2 = "test-session-2"
    query2 = "plan journey from 12th block nagarbhavi to banashankari"
    print(f"Sending: '{query2}'")
    
    intent_result2 = await ai_assistant_service.detect_intent(query2, session_id2)
    print("Intent detected:", intent_result2.get('intent'))
    print("Extracted source:", intent_result2.get('parameters', {}).get('origin', 'Not Found'))
    print("Extracted destination:", intent_result2.get('parameters', {}).get('destination', 'Not Found'))
    
    tool_call2 = await ai_assistant_service.execute_tool(
        intent=intent_result2.get('intent'),
        parameters=intent_result2.get('parameters', {}),
        session_id=session_id2
    )
    print("Tool selected:", tool_call2.tool_name)
    
    final_response2 = await ai_assistant_service.format_response(tool_call2, query2)
    print("Final response:", final_response2)

if __name__ == "__main__":
    asyncio.run(main())
