"""
AI API Endpoints
----------------
API endpoints for CatBoost model inference, model status monitoring, and AI Transit Assistant.

Endpoints:
- POST /api/ai/predict-demand - Predict passenger demand with complete feature set
- GET /api/ai/model-status - Get model status and metadata
- GET /ai/health - Health check for AI services
- POST /api/ai/assistant/chat - AI Transit Assistant chat endpoint
"""

import logging
import uuid
import re
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database.connection import get_db

from app.ml.model_loader import model_loader
from app.ml.predictor import predictor
from app.services.demand_prediction_service import demand_prediction_service
from app.services.ai_assistant_service import ai_assistant_service
from app.logger import app_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI"])


class ChatRequest(BaseModel):
    """Request model for AI Assistant chat."""
    message: str = Field(..., min_length=1, max_length=1000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Sanitize user message to prevent injection attacks."""
        # Remove any potential script tags or dangerous patterns
        v = re.sub(r'<script.*?>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r'<.*?>', '', v)  # Remove HTML tags
        return v.strip()


class ChatResponse(BaseModel):
    """Response model for AI Assistant chat."""
    response: str = Field(..., description="AI's response")
    intent: Optional[str] = Field(None, description="Detected intent")
    tool_used: Optional[str] = Field(None, description="Tool that was called")
    execution_time_ms: float = Field(..., description="Total execution time in milliseconds")
    session_id: str = Field(..., description="Session ID")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="Structured data from tool result")


@router.post("/predict-demand")
async def predict_demand(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict passenger demand using CatBoost model with complete feature set.
    
    This endpoint accepts a complete feature dictionary matching the training schema
    (57 features) and returns the predicted passenger count along with metadata.
    
    Request Body:
        Complete feature dictionary with all 57 features used during training.
        Required features include: route_id, stop_id, hour, weather_condition, 
        traffic_level, and all other features from the training schema.
    
    Returns:
        {
            "success": bool,
            "predicted_passenger_count": int,
            "confidence_score": float,
            "demand_class": str,
            "inference_time_ms": float,
            "model_version": str,
            "model_source": str,
            "error": str | None
        }
    
    Example Request:
        {
            "route_id": "123",
            "stop_id": "456",
            "hour": 14,
            "weather_condition": "Clear",
            "traffic_level": "Medium",
            ... (all other 52 features)
        }
    
    Example Response:
        {
            "success": true,
            "predicted_passenger_count": 42,
            "confidence_score": 0.974,
            "demand_class": "Medium",
            "inference_time_ms": 12.5,
            "model_version": "2025-01-15",
            "model_source": "catboost",
            "error": null
        }
    """
    try:
        logger.info(f"Received prediction request with {len(features)} features")
        
        # Validate that features are provided
        if not features:
            raise HTTPException(status_code=400, detail="No features provided")
        
        # Delegate to predictor
        result = predictor.predict_passenger_count(features)
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Prediction failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict_demand: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/model-status")
async def get_model_status() -> Dict[str, Any]:
    """
    Get CatBoost model status and metadata.
    
    Returns information about the loaded model including:
    - Model loaded status
    - Algorithm type
    - Feature count
    - Training metrics (RMSE, MAE, R², MAPE)
    - Model configuration
    - Model path
    
    Returns:
        {
            "model_loaded": bool,
            "model_path": str,
            "algorithm": str,
            "feature_count": int,
            "categorical_feature_count": int,
            "training_metrics": {
                "RMSE": float,
                "MAE": float,
                "R2": float,
                "MAPE": float
            },
            "model_config": dict,
            "status": str
        }
    """
    try:
        model_info = model_loader.get_model_info()
        
        # Add overall status
        if model_info["model_loaded"]:
            model_info["status"] = "ready"
        else:
            model_info["status"] = "not_loaded"
        
        logger.info(f"Model status requested: {model_info['status']}")
        return model_info
        
    except Exception as e:
        logger.error(f"Error getting model status: {e}", exc_info=True)
        return {
            "model_loaded": False,
            "status": "error",
            "error": str(e)
        }


@router.get("/health")
async def ai_health() -> Dict[str, Any]:
    """
    Health check for AI services.
    
    Returns the health status of the AI inference system including:
    - Model loaded status
    - Inference ready status
    - Average inference time (if available)
    - Feature count
    - Backend status
    
    Returns:
        {
            "status": str,  # "healthy" | "degraded" | "unhealthy"
            "model_loaded": bool,
            "inference_ready": bool,
            "feature_count": int,
            "backend_status": str,
            "timestamp": str
        }
    """
    try:
        model_loaded = model_loader.is_model_loaded()
        inference_ready = model_loaded and model_loader.get_model() is not None
        feature_count = len(model_loader.get_feature_names())
        
        # Determine overall status
        if model_loaded and inference_ready:
            status = "healthy"
        elif model_loaded:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "model_loaded": model_loaded,
            "inference_ready": inference_ready,
            "feature_count": feature_count,
            "backend_status": "running" if model_loaded else "model_not_loaded",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in AI health check: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "model_loaded": False,
            "inference_ready": False,
            "feature_count": 0,
            "backend_status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/assistant/chat", response_model=ChatResponse)
async def assistant_chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    AI Transit Assistant chat endpoint.
    
    This endpoint processes natural language queries from passengers,
    detects intent using Grok API, calls appropriate backend tools,
    and returns formatted responses.
    
    Request Body:
        {
            "message": "User's message",
            "session_id": "Optional session ID for conversation context"
        }
    
    Returns:
        {
            "response": "AI's response",
            "intent": "Detected intent",
            "tool_used": "Tool that was called",
            "execution_time_ms": "Total execution time",
            "session_id": "Session ID",
            "structured_data": "Structured data from tool result"
        }
    """
    import time
    
    start_time = time.time()
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Log the user query
        app_logger.info(
            "AI Assistant chat request",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "message": request.message[:200],
                }
            }
        )
        
        # Detect intent
        intent_result = await ai_assistant_service.detect_intent(request.message, session_id)
        
        intent = intent_result.get("intent", "general_query")
        parameters = intent_result.get("parameters", {})
        
        # If it's a general query or unclear intent, provide a helpful response
        if intent == "general_query" or intent not in ai_assistant_service.tools:
            execution_time_ms = (time.time() - start_time) * 1000
            
            return ChatResponse(
                response="I'd be happy to help you with your transit journey! You can ask me about:\n\n"
                        "• Planning a journey (e.g., \"Plan my journey to Majestic\")\n"
                        "• Alternative routes (e.g., \"Show me another route\")\n"
                        "• Bus arrival times (e.g., \"When will the next bus arrive?\")\n"
                        "• Service alerts (e.g., \"Are there any service alerts?\")\n"
                        "• Weather conditions (e.g., \"What's the weather like?\")\n\n"
                        "What would you like to know?",
                intent=intent,
                tool_used=None,
                execution_time_ms=execution_time_ms,
                session_id=session_id,
                structured_data=None
            )
        
        # Execute the appropriate tool
        tool_call = await ai_assistant_service.execute_tool(intent, parameters, session_id, db)
        
        # Format the response
        response = await ai_assistant_service.format_response(tool_call, request.message)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Extract structured data if available
        structured_data = None
        if tool_call.success and tool_call.result:
            structured_data = tool_call.result
        
        return ChatResponse(
            response=response,
            intent=intent,
            tool_used=tool_call.tool_name,
            execution_time_ms=execution_time_ms,
            session_id=session_id,
            structured_data=structured_data
        )
        
    except Exception as e:
        logger.error(f"Error in AI Assistant chat: {e}", exc_info=True)
        execution_time_ms = (time.time() - start_time) * 1000
        
        return ChatResponse(
            response="I apologize, but I encountered an error processing your request. Please try again.",
            intent="error",
            tool_used=None,
            execution_time_ms=execution_time_ms,
            session_id=session_id,
            structured_data=None
        )


@router.post("/assistant/clear-context")
async def clear_context(session_id: str) -> Dict[str, Any]:
    """
    Clear conversation context for a session.
    
    This endpoint resets the conversation memory for a given session ID.
    
    Request Body:
        {
            "session_id": "Session ID to clear"
        }
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        ai_assistant_service.clear_context(session_id)
        return {
            "success": True,
            "message": "Conversation context cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing context: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to clear context: {str(e)}"
        }
