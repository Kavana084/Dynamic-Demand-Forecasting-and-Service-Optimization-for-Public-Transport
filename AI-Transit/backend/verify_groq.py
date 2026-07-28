import asyncio
import sys

# Force UTF-8 output to avoid Windows cp1252 encoding errors on special chars
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from app.config import settings
from app.services.ai_assistant_service import ai_assistant_service

print("=== Groq Config ===")
print("API_KEY_PRESENT", bool(settings.groq_api_key))
print("MODEL", settings.groq_model)
print("URL", settings.groq_api_url)

async def run_test(label, query, session_id):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"QUERY: {query}")
    print('='*60)
    
    intent_result = await ai_assistant_service.detect_intent(query, session_id)
    
    print(f"  -> INTENT:     {intent_result.get('intent')}")
    print(f"  -> PARAMETERS: {intent_result.get('parameters')}")
    print(f"  -> CONFIDENCE: {intent_result.get('confidence')}")
    
    tool_call = await ai_assistant_service.execute_tool(
        intent=intent_result.get('intent'),
        parameters=intent_result.get('parameters', {}),
        session_id=session_id
    )
    
    print(f"  -> TOOL_SUCCESS: {tool_call.success}")
    if tool_call.error:
        print(f"  -> TOOL_ERROR: {tool_call.error}")
    if tool_call.result:
        print(f"  -> TOOL_RESULT (keys): {list(tool_call.result.keys())}")
    
    final = await ai_assistant_service.format_response(tool_call, query)
    print(f"  -> FINAL RESPONSE: {final}")

async def main():
    await run_test(
        "Journey Planning",
        "Plan journey from 12th block nagarbhavi to banashankari",
        "test-journey"
    )
    await run_test(
        "Route Info",
        "What is route 2872?",
        "test-route"
    )
    await run_test(
        "Crowd Info",
        "How crowded is route 2872?",
        "test-crowd"
    )

if __name__ == "__main__":
    asyncio.run(main())
