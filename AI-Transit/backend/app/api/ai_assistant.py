"""
AI Assistant API Router
-----------------------
Provides the /api/ai-assistant/chat endpoint for the AI Transit Assistant.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import time

from app.services.ai_assistant_service import ai_assistant_service
from app.logger import app_logger
from app.database.connection import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(prefix="/api/ai-assistant", tags=["ai-assistant"])


class ChatRequest(BaseModel):
    """Request model for AI Assistant chat."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for AI Assistant chat."""
    answer: str
    confidence: float
    sources: list = []
    session_id: str
    tool_used: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, db: Session = Depends(get_db)):
    """
    Process a chat message with the AI Transit Assistant.
    
    This endpoint:
    - Detects passenger intent
    - Routes to appropriate backend tools
    - Maintains conversation context
    - Returns passenger-friendly responses
    """
    # Generate or use session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    print("CHAT_ENDPOINT_HIT")
    print("USER_QUERY", request.message)
    
    # Log the request
    app_logger.info(
        "AI_ASSISTANT_REQUEST",
        extra={
            "extra_data": {
                "session_id": session_id,
                "message": request.message[:200],
                "endpoint": "/api/ai-assistant/chat"
            }
        }
    )
    
    try:
        # Detect intent
        intent_result = await ai_assistant_service.detect_intent(
            query=request.message,
            session_id=session_id
        )
        
        # Log Groq request status
        from app.config import settings
        app_logger.info(
            "AI_ASSISTANT_GROQ_REQUEST",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "message": request.message[:100],
                    "api_key_configured": bool(settings.groq_api_key),
                    "using_fallback": not bool(settings.groq_api_key)
                }
            }
        )
        
        # Log intent detection
        app_logger.info(
            "AI_ASSISTANT_INTENT",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "intent": intent_result.get("intent"),
                    "confidence": intent_result.get("confidence"),
                    "parameters": intent_result.get("parameters", {})
                }
            }
        )
        
        # Log extracted entities
        app_logger.info(
            "AI_ASSISTANT_ENTITIES",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "origin": intent_result.get("parameters", {}).get("origin"),
                    "destination": intent_result.get("parameters", {}).get("destination"),
                    "route_id": intent_result.get("parameters", {}).get("route_id")
                }
            }
        )
        
        # Execute tool
        tool_call = await ai_assistant_service.execute_tool(
            intent=intent_result.get("intent"),
            parameters=intent_result.get("parameters", {}),
            session_id=session_id,
            db=db
        )
        
        # Log tool call
        app_logger.info(
            "AI_ASSISTANT_TOOL_CALL",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "tool_name": tool_call.tool_name,
                    "parameters": tool_call.parameters,
                    "success": tool_call.success,
                    "execution_time_ms": tool_call.execution_time_ms
                }
            }
        )
        
        # Format response
        answer = await ai_assistant_service.format_response(
            tool_call=tool_call,
            query=request.message
        )
        
        # Log response
        app_logger.info(
            "AI_ASSISTANT_RESPONSE",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "answer": answer[:200],
                    "tool_name": tool_call.tool_name,
                    "success": tool_call.success,
                    "execution_time_ms": tool_call.execution_time_ms
                }
            }
        )
        
        # Populate tool_used and structured_data for frontend
        tool_used = tool_call.tool_name if tool_call.success else None
        structured_data = tool_call.result if tool_call.success else None
        
        return ChatResponse(
            answer=answer,
            confidence=intent_result.get("confidence", 0.5),
            sources=[],
            session_id=session_id,
            tool_used=tool_used,
            structured_data=structured_data
        )
        
    except Exception as e:
        app_logger.error(
            "AI_ASSISTANT_ERROR",
            exc_info=True,
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "message": request.message[:200],
                    "error": str(e)
                }
            }
        )
        
        # Return fallback response
        return ChatResponse(
            answer="I can help with route planning, crowd levels, travel times, and bus availability. Tell me where you'd like to travel.",
            confidence=0.0,
            sources=[],
            session_id=session_id,
            tool_used=None,
            structured_data=None
        )


@router.post("/clear-context")
async def clear_context(session_id: str):
    """
    Clear conversation context for a session.
    """
    ai_assistant_service.clear_context(session_id)
    
    app_logger.info(
        "AI_ASSISTANT_CONTEXT_CLEARED",
        extra={
            "extra_data": {
                "session_id": session_id
            }
        }
    )
    
    return {"status": "success", "message": "Context cleared"}
