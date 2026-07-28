"""
AI Transit Assistant Service
----------------------------
Service for the AI Transit Assistant using Groq API for natural language understanding
and existing backend services for transit data.

This service:
- Detects passenger intent using Groq API
- Routes to appropriate backend tools
- Maintains conversation context
- Formats responses in passenger-friendly language
"""

import json
import time
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session

from app.config import settings
from app.logger import app_logger
from app.database.connection import get_db
from app.services.routing_service import resolve_route_dynamic, generate_alternative_routes
from app.api.navigation import plan_navigation
from app.database.models import GTFSStop, DemandHistory
from app.services.demand_prediction_service import demand_prediction_service
from app.services.analytics_service import AnalyticsService
from app.services.fleet_optimization_service import FleetOptimizationService


@dataclass
class ConversationContext:
    """Stores conversation context for maintaining state across messages."""
    origin: Optional[str] = None
    destination: Optional[str] = None
    route_id: Optional[str] = None
    last_intent: Optional[str] = None
    last_tool: Optional[str] = None
    message_count: int = 0


@dataclass
class ToolCall:
    """Represents a backend tool call."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None


class AIAssistantService:
    """AI Transit Assistant Service using Groq API for intent detection."""
    
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.api_url = settings.groq_api_url
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        
        # Define available tools
        self.tools = {
            "plan_trip": self._plan_trip,
            "get_alternative_routes": self._get_alternative_routes,
            "get_crowd_info": self._get_crowd_info,
            "get_service_info": self._get_service_info,
            "get_travel_time": self._get_travel_time,
            "get_route_info": self._get_route_info,
            "get_demand_insights": self._get_demand_insights,
            "get_busiest_routes": self._get_busiest_routes,
            "get_fleet_recommendations": self._get_fleet_recommendations,
        }
        
        # Passenger-friendly language translation layer
        self.crowd_mapping = {
            (0, 20): "Very Comfortable",
            (21, 40): "Comfortable",
            (41, 60): "Moderately Busy",
            (61, 80): "Busy",
            (81, 999): "Very Crowded"
        }
        
        self.bus_availability_mapping = {
            1: "Limited Service",
            2: "Regular Service",
            3: "Frequent Service",
            4: "Frequent Service",
            5: "Very Frequent Service"
        }
        
        self.seating_mapping = {
            (90, 100): "Seats Easily Available",
            (70, 89): "Seats Likely Available",
            (40, 69): "Limited Seating",
            (20, 39): "Standing Likely",
            (0, 19): "Very Crowded"
        }
        
        # System prompt for intent detection
        self.system_prompt = """You are an AI Transit Assistant for a smart transit system. Your role is to:

1. Understand the passenger's natural language query
2. Detect their intent (journey planning, bus tracking, service alerts, etc.)
3. Extract ALL relevant parameters from the query text (origin, destination, route_id, etc.)
4. Decide which backend tool to call

Available tools:
- plan_trip: For journey planning (needs origin AND destination extracted from query)
- get_alternative_routes: For alternative route options (needs origin, destination)
- get_crowd_info: For crowd level information (needs route_id, or origin and destination)
- get_service_info: For bus service frequency and availability (needs route_id or origin, destination)
- get_travel_time: For travel time estimates (needs origin, destination)
- get_route_info: For information about a specific route (needs route_id)
- get_demand_insights: For overall demand insights or network passenger demand metrics
- get_busiest_routes: For a list of the highest demand or busiest routes
- get_fleet_recommendations: For fleet sizing or optimization recommendations (needs route_id, or general)

CRITICAL RULES:
- For plan_trip: ALWAYS extract origin and destination from the query text. For example, "Plan journey from 12th block nagarbhavi to banashankari" → origin="12th block nagarbhavi", destination="banashankari"
- For get_route_info: extract the route identifier (may contain letters, numbers, and hyphens). Examples: "What is route 2872?" → route_id="2872". "What is route 500-LA?" → route_id="500-LA". "Tell me about route 244-C VSD" → route_id="244-C VSD"
- For get_crowd_info: if a route identifier is mentioned (e.g. "route 2872" or "route 600-A"), extract it as route_id
- Route identifiers can be purely numeric (2872), alphanumeric (500-LA, 600-A, 296-D), or contain spaces (244-C VSD, KLN-HBR)
- ALWAYS include the extracted parameters in the response

You MUST respond with ONLY a valid JSON object (no other text, no markdown) in this exact format:
{"intent": "tool_name", "parameters": {"origin": "...", "destination": "..."}, "confidence": 0.9}

Examples:
- "Plan journey from 12th block nagarbhavi to banashankari" → {"intent": "plan_trip", "parameters": {"origin": "12th block nagarbhavi", "destination": "banashankari"}, "confidence": 0.98}
- "What is route 2872?" → {"intent": "get_route_info", "parameters": {"route_id": "2872"}, "confidence": 0.99}
- "What is route 500-LA?" → {"intent": "get_route_info", "parameters": {"route_id": "500-LA"}, "confidence": 0.99}
- "Tell me about route 244-C VSD" → {"intent": "get_route_info", "parameters": {"route_id": "244-C VSD"}, "confidence": 0.98}
- "How crowded is route 2872?" → {"intent": "get_crowd_info", "parameters": {"route_id": "2872"}, "confidence": 0.97}
- "How crowded is route 600-A?" → {"intent": "get_crowd_info", "parameters": {"route_id": "600-A"}, "confidence": 0.97}
- "Which routes are experiencing high demand?" → {"intent": "get_busiest_routes", "parameters": {}, "confidence": 0.95}
- "Show demand insights for today." → {"intent": "get_demand_insights", "parameters": {}, "confidence": 0.95}
- "What are the busiest routes right now?" → {"intent": "get_busiest_routes", "parameters": {}, "confidence": 0.95}
- "Show fleet recommendations." → {"intent": "get_fleet_recommendations", "parameters": {}, "confidence": 0.95}

If the intent is unclear, use {"intent": "general_query", "parameters": {}, "confidence": 0.5}"""
    
    def _get_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context for a session."""
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = ConversationContext()
        return self.conversation_contexts[session_id]
    
    def _update_context(self, session_id: str, intent: str, parameters: Dict[str, Any]):
        """Update conversation context with new information."""
        context = self._get_context(session_id)
        context.last_intent = intent
        context.message_count += 1
        
        if 'origin' in parameters:
            context.origin = parameters['origin']
        if 'destination' in parameters:
            context.destination = parameters['destination']
        if 'route_id' in parameters:
            context.route_id = parameters['route_id']
    
    async def _call_groq_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call Groq API for intent detection."""
        if not self.api_key:
            app_logger.warning("Groq API key not configured, using fallback intent detection")
            return self._fallback_intent_detection(messages[-1]['content'])
        
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        print("LLM_PROVIDER", "Groq")
        print("GROQ_REQUEST_START")
        print("GROQ_URL", settings.groq_api_url)
        print("MODEL", settings.groq_model)
        print("API_KEY_PRESENT", bool(settings.groq_api_key))
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                print("GROQ_STATUS", response.status_code)
                raw_text = response.text
                print("RAW_GROQ_RESPONSE", raw_text[:2000])
                
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("GROQ_CONTENT", content)
                
                parsed = json.loads(content)
                print("PARSED_INTENT", parsed.get('intent'))
                print("PARSED_PARAMETERS", parsed.get('parameters'))
                return parsed
        except httpx.TimeoutException:
            app_logger.error("Groq API request timed out")
            return self._fallback_intent_detection(messages[-1]['content'])
        except httpx.HTTPStatusError as e:
            app_logger.error(f"Groq API HTTP error: {e.response.status_code} body={e.response.text}")
            return self._fallback_intent_detection(messages[-1]['content'])
        except json.JSONDecodeError as e:
            app_logger.error(f"Failed to parse Groq API response: {e} content={content!r}")
            return self._fallback_intent_detection(messages[-1]['content'])
        except Exception as e:
            app_logger.error(f"Error calling Groq API: {e}")
            return self._fallback_intent_detection(messages[-1]['content'])
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract origin and destination entities from natural language query."""
        import re
        
        query_lower = query.lower()
        parameters = {}
        
        # Common stop/location names (sample - in production, this would come from database)
        # For now, we'll extract any capitalized or proper noun-like patterns
        # Since we're dealing with place names like "Nagarabhavi", "Majestic", "MG Road", etc.
        
        # Pattern 1: "from [Origin] to [Destination]"
        # This pattern looks for the word "from" followed by text, then "to" followed by text
        # We use a more specific pattern to avoid capturing the "from" and "to" keywords themselves
        from_pattern = r'from\s+([a-z]+(?:\s+[a-z]+)?)\s+to\s+([a-z]+(?:\s+[a-z]+)?)'
        match = re.search(from_pattern, query_lower)
        
        if match:
            origin = match.group(1).strip()
            destination = match.group(2).strip()
            
            # Filter out common non-location words
            origin_words = origin.split()
            dest_words = destination.split()
            
            # Remove common stop words from beginning
            stop_words = ['travel', 'plan', 'journey', 'trip', 'get', 'how', 'do', 'i', 'my', 'take', 'me', 'go']
            
            origin_clean = ' '.join([w for w in origin_words if w not in stop_words])
            dest_clean = ' '.join([w for w in dest_words if w not in stop_words])
            
            if origin_clean and dest_clean:
                parameters['origin'] = origin_clean
                parameters['destination'] = dest_clean
                return parameters
        
        # Pattern 2: "[Origin] to [Destination]" (without "from")
        # Only match if the query starts with a location-like word
        to_pattern = r'^([a-z]+(?:\s+[a-z]+)?)\s+to\s+([a-z]+(?:\s+[a-z]+)?)'
        match = re.search(to_pattern, query_lower)
        
        if match:
            origin = match.group(1).strip()
            destination = match.group(2).strip()
            
            # Filter out common non-location words
            origin_words = origin.split()
            dest_words = destination.split()
            
            stop_words = ['travel', 'plan', 'journey', 'trip', 'get', 'how', 'do', 'i', 'my', 'take', 'me', 'go']
            
            origin_clean = ' '.join([w for w in origin_words if w not in stop_words])
            dest_clean = ' '.join([w for w in dest_words if w not in stop_words])
            
            if origin_clean and dest_clean:
                parameters['origin'] = origin_clean
                parameters['destination'] = dest_clean
        
        return parameters
    
    def _fallback_intent_detection(self, query: str) -> Dict[str, Any]:
        """Fallback intent detection using keyword matching."""
        query_lower = query.lower()
        
        # Journey planning
        if any(word in query_lower for word in ['plan', 'journey', 'route', 'reach', 'take me', 'go to', 'how to get', 'to']):
            parameters = self._extract_entities(query)
            return {
                "intent": "plan_trip",
                "parameters": parameters,
                "confidence": 0.7
            }
        
        # Alternative routes
        if any(word in query_lower for word in ['alternative', 'another route', 'other option', 'different route']):
            return {
                "intent": "get_alternative_routes",
                "parameters": {},
                "confidence": 0.8
            }
        
        # General query
        return {
            "intent": "general_query",
            "parameters": {},
            "confidence": 0.5
        }
    
    async def detect_intent(self, query: str, session_id: str) -> Dict[str, Any]:
        """Detect passenger intent using Groq API."""
        print("RAW_USER_QUERY", query)
        context = self._get_context(session_id)
        
        # Build messages with context
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add context information
        if context.origin or context.destination:
            context_info = "Current journey context: "
            if context.origin:
                context_info += f"Origin: {context.origin}. "
            if context.destination:
                context_info += f"Destination: {context.destination}. "
            messages.append({"role": "system", "content": context_info})
        
        messages.append({"role": "user", "content": query})
        
        # Call Groq API
        start_time = time.time()
        intent_result = await self._call_groq_api(messages)
        
        execution_time = (time.time() - start_time) * 1000
        
        app_logger.info(
            "Intent detection completed",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "query": query[:100],
                    "intent": intent_result.get("intent"),
                    "confidence": intent_result.get("confidence"),
                    "execution_time_ms": execution_time,
                }
            }
        )
        
        return intent_result
    
    async def execute_tool(self, intent: str, parameters: Dict[str, Any], session_id: str, db: Session = None) -> ToolCall:
        """Execute the appropriate backend tool."""
        print("TOOL_SELECTED", intent)
        print("TOOL_PARAMETERS", parameters)
        tool_call = ToolCall(
            tool_name=intent,
            parameters=parameters
        )
        
        start_time = time.time()
        
        try:
            # Get context to fill in missing parameters
            context = self._get_context(session_id)
            
            # Fill in missing parameters from context
            if 'origin' not in parameters and context.origin:
                parameters['origin'] = context.origin
            if 'destination' not in parameters and context.destination:
                parameters['destination'] = context.destination
            if 'route_id' not in parameters and context.route_id:
                parameters['route_id'] = context.route_id
            
            # Execute the tool
            if intent in self.tools:
                result = await self.tools[intent](parameters, session_id, db)
                tool_call.result = result
                # Check if the tool itself reported success
                tool_call.success = result.get('success', True)
                
                # Update context with new information
                self._update_context(session_id, intent, parameters)
            else:
                tool_call.error = f"Unknown tool: {intent}"
                tool_call.success = False
                
        except Exception as e:
            app_logger.error(f"Error executing tool {intent}: {e}", exc_info=True)
            tool_call.error = str(e)
            tool_call.success = False
        
        tool_call.execution_time_ms = (time.time() - start_time) * 1000
        
        app_logger.info(
            "Tool execution completed",
            extra={
                "extra_data": {
                    "session_id": session_id,
                    "tool_name": intent,
                    "success": tool_call.success,
                    "execution_time_ms": tool_call.execution_time_ms,
                }
            }
        )
        
        return tool_call
    
    async def _plan_trip(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Plan a journey using the routing service."""
        try:
            # Convert stop names to IDs if needed
            origin_name = parameters.get('origin')
            destination_name = parameters.get('destination')
            
            if not origin_name or not destination_name:
                return {
                    "success": False,
                    "error": "Both origin and destination are required for journey planning",
                    "message": "Please tell me where you're travelling from and where you want to go."
                }
            
            # Resolve stop names to stop IDs
            source_id = self._resolve_stop_id(origin_name, db)
            destination_id = self._resolve_stop_id(destination_name, db)
            
            if not source_id:
                return {
                    "success": False,
                    "error": f"Could not find stop: {origin_name}",
                    "message": f"I couldn't find a stop called '{origin_name}'. Please check the spelling or try a different stop name."
                }
            
            if not destination_id:
                return {
                    "success": False,
                    "error": f"Could not find stop: {destination_name}",
                    "message": f"I couldn't find a stop called '{destination_name}'. Please check the spelling or try a different stop name."
                }
            
            app_logger.info(
                f"AI Assistant planning trip: {origin_name} ({source_id}) -> {destination_name} ({destination_id})"
            )
            
            # Call the navigation endpoint with timeout to prevent long hangs
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        plan_navigation,
                        source_id=source_id,
                        destination_id=destination_id,
                        request=None,
                        db=db
                    ),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                app_logger.error(f"AI Assistant trip planning timed out after 15s: {origin_name} -> {destination_name}")
                return {
                    "success": False,
                    "error": "Trip planning timed out",
                    "message": "Finding a route took too long. Please try a different origin/destination or try again later."
                }
            
            return result
        except Exception as e:
            app_logger.error(f"Error in _plan_trip: {e}")
            return {"success": False, "error": str(e), "message": "An error occurred while planning your trip."}

    async def _get_alternative_routes(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get alternative routes for a journey."""
        try:
            source_id = parameters.get('origin')
            destination_id = parameters.get('destination')
            
            if not source_id or not destination_id:
                return {
                    "success": False,
                    "error": "Both origin and destination are required",
                    "message": "I need to know your origin and destination to find alternative routes."
                }
            
            alternatives = generate_alternative_routes(
                db=db,
                source_id=source_id,
                destination_id=destination_id
            )
            
            return {
                "success": True,
                "alternative_routes": alternatives,
                "count": len(alternatives)
            }
            
        except Exception as e:
            app_logger.error(f"Error in _get_alternative_routes: {e}")
            return {"success": False, "error": str(e), "message": "An error occurred while getting alternative routes."}

    async def _get_crowd_info(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get crowd level information using passenger-friendly language.
        
        Accepts route_id (numeric) or route_short_name (e.g. 600-A).
        Resolves route_short_name to route_id before crowd prediction.
        """
        context = self._get_context(session_id)
        
        route_identifier = parameters.get('route_id') or parameters.get('route_short_name')
        origin = parameters.get('origin') or context.origin
        destination = parameters.get('destination') or context.destination
        
        if route_identifier:
            try:
                route = self._resolve_route(route_identifier, db)
                if route:
                    resolved_route_id = route.route_id
                    resolved_short_name = getattr(route, 'route_short_name', route_identifier)
                    
                    # Fetch real values for the feature vector
                    now = datetime.now()
                    current_hour = now.hour
                    current_day = now.weekday() + 1
                    
                    recent_demand = db.query(DemandHistory).filter(
                        DemandHistory.route_id == resolved_route_id
                    ).order_by(DemandHistory.timestamp.desc()).first()
                    
                    if recent_demand:
                        real_passenger_count = recent_demand.passenger_count
                        real_occupancy_ratio = getattr(recent_demand, 'occupancy_percent', 60.0) / 100.0
                    else:
                        real_passenger_count = 50
                        real_occupancy_ratio = 0.6
                        
                    features = {
                        "route_id": resolved_route_id,
                        "passenger_count": real_passenger_count,
                        "occupancy_ratio": real_occupancy_ratio,
                        "hour": current_hour,
                        "day_of_week": current_day
                    }
                    
                    app_logger.info(f"ROUTE_ID {resolved_route_id}")
                    app_logger.info(f"FEATURE_VECTOR {features}")
                    
                    # CALL REAL PREDICTION SERVICE
                    prediction = demand_prediction_service.predict(features)
                    journey_demand = prediction.get("journey_predicted_passengers", 50)
                    model_source = prediction.get("model_source", "unknown")
                    crowd_level = self._translate_crowd_level(journey_demand)
                    
                    app_logger.info(f"MODEL_SOURCE {model_source}")
                    app_logger.info(f"JOURNEY_PREDICTED_PASSENGERS {journey_demand}")
                    app_logger.info(f"CROWD_LEVEL {crowd_level}")
                    
                    return {
                        "success": True,
                        "route_id": resolved_route_id,
                        "route_short_name": resolved_short_name,
                        "predicted_demand": journey_demand,
                        "crowd_level": crowd_level,
                        "message": (
                            f"Route {resolved_short_name} is currently {crowd_level.lower()}. "
                            f"Predicted passenger count is {journey_demand}."
                        )
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Route '{route_identifier}' not found",
                        "message": (
                            f"I couldn't find route {route_identifier}. "
                            "Please check the route number and try again."
                        )
                    }
            except Exception as e:
                app_logger.error(f"Error in _get_crowd_info route logic: {e}")
                return {"success": False, "error": str(e), "message": "An error occurred."}
        
        # If no route context, ask for journey details
        if not origin or not destination:
            return {
                "success": False,
                "error": "No route context",
                "message": "I can help with crowd level information. Please tell me the route number, or where you're travelling from and where you want to go."
            }
        
        # Get journey data to extract crowd information
        try:
            result = plan_navigation(
                source_id=origin,
                destination_id=destination,
                request=None,
                db=db
            )
            
            if not result.get('success'):
                return {
                    "success": False,
                    "error": "Failed to get journey data",
                    "message": "I couldn't retrieve the crowd information for this route. Please try again."
                }
            
            predicted_demand = result.get('predicted_demand', 0)
            crowd_level = self._translate_crowd_level(predicted_demand)
            
            return {
                "success": True,
                "predicted_demand": predicted_demand,
                "crowd_level": crowd_level,
                "route_id": result.get('route_id')
            }
            
        except Exception as e:
            app_logger.error(f"Error in _get_crowd_info journey logic: {e}")
            return {"success": False, "error": str(e), "message": "An error occurred."}
    
    async def _get_service_info(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get bus service frequency and availability information."""
        context = self._get_context(session_id)
        
        # If no route context, ask for journey details
        if not context.origin or not context.destination:
            return {
                "success": False,
                "error": "No route context",
                "message": "I can help with service information. Please tell me where you're travelling from and where you want to go."
            }
        
        # Get journey data to extract service information
        try:
            result = plan_navigation(
                source_id=context.origin,
                destination_id=context.destination,
                request=None,
                db=db
            )
            
            if not result.get('success'):
                return {
                    "success": False,
                    "error": "Failed to get journey data",
                    "message": "I couldn't retrieve the service information for this route. Please try again."
                }
            
            recommended_fleet = result.get('recommended_fleet', 1)
            service_level = self._translate_bus_availability(recommended_fleet)
            headway_minutes = result.get('service_frequency', {}).get('headway_minutes', 0)
            
            return {
                "success": True,
                "recommended_fleet": recommended_fleet,
                "service_level": service_level,
                "headway_minutes": headway_minutes,
                "route_id": result.get('route_id')
            }
            
        except Exception as e:
            app_logger.error(f"Error in _get_service_info: {e}")
            return {"success": False, "error": str(e), "message": "An error occurred."}
    
    async def _get_travel_time(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get travel time estimates."""
        context = self._get_context(session_id)
        
        # If no route context, ask for journey details
        if not context.origin or not context.destination:
            return {
                "success": False,
                "error": "No route context",
                "message": "I can help with travel time estimates. Please tell me where you're travelling from and where you want to go."
            }
        
        # Get journey data to extract travel time information
        try:
            result = plan_navigation(
                source_id=context.origin,
                destination_id=context.destination,
                request=None,
                db=db
            )
            
            if not result.get('success'):
                return {
                    "success": False,
                    "error": "Failed to get journey data",
                    "message": "I couldn't retrieve the travel time for this route. Please try again."
                }
            
            eta_minutes = result.get('eta_minutes', 0)
            distance_km = result.get('distance_km', 0)
            transfers = result.get('transfers', 0)
            
            return {
                "success": True,
                "eta_minutes": eta_minutes,
                "distance_km": distance_km,
                "transfers": transfers,
                "route_id": result.get('route_id')
            }
            
        except Exception as e:
            app_logger.error(f"Error in _get_travel_time: {e}")
            return {"success": False, "error": str(e), "message": "An error occurred."}

    async def _get_demand_insights(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get overall demand insights using analytics service."""
        try:
            summary = AnalyticsService.get_dashboard_summary(db)
            return {
                "success": True,
                "summary": summary
            }
        except Exception as e:
            app_logger.error(f"Error getting demand insights: {e}")
            return {"success": False, "error": str(e), "message": "Failed to retrieve demand insights."}

    async def _get_busiest_routes(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get busiest routes using analytics service."""
        try:
            top_routes = AnalyticsService.get_top_routes(db, limit=5)
            return {
                "success": True,
                "top_routes": top_routes
            }
        except Exception as e:
            app_logger.error(f"Error getting busiest routes: {e}")
            return {"success": False, "error": str(e), "message": "Failed to retrieve busiest routes."}

    async def _get_fleet_recommendations(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get fleet recommendations."""
        try:
            top_routes = AnalyticsService.get_top_routes(db, limit=5)
            route_demands = {r["route_id"]: r["average_passenger_count"] for r in top_routes}
            
            optimizer = FleetOptimizationService()
            recommendations = optimizer.batch_optimize(route_demands=route_demands)
            return {
                "success": True,
                "recommendations": recommendations
            }
        except Exception as e:
            app_logger.error(f"Error getting fleet recommendations: {e}")
            return {"success": False, "error": str(e), "message": "Failed to retrieve fleet recommendations."}
    
    def _translate_crowd_level(self, predicted_demand: int) -> str:
        """Translate predicted demand to passenger-friendly crowd level."""
        for (low, high), description in self.crowd_mapping.items():
            if low <= predicted_demand <= high:
                return description
        return "Unknown"
    
    def _translate_bus_availability(self, recommended_fleet: int) -> str:
        """Translate fleet count to passenger-friendly service level."""
        return self.bus_availability_mapping.get(recommended_fleet, "Unknown")
    
    def _translate_seating_chance(self, occupancy_percent: int) -> str:
        """Translate occupancy to passenger-friendly seating chance."""
        for (low, high), description in self.seating_mapping.items():
            if low <= occupancy_percent <= high:
                return description
        return "Unknown"
    
    def _resolve_route(self, route_identifier: str, db) -> Optional[Any]:
        """Resolve a route by route_id or route_short_name.
        
        Search strategy:
        1. Exact match on route_id
        2. Case-insensitive match on route_short_name
        
        Logs ROUTE_LOOKUP_INPUT, ROUTE_LOOKUP_TYPE, and ROUTE_LOOKUP_RESULT.
        Returns the Route ORM object, or None if not found.
        """
        from app.database.models import Route
        
        app_logger.info(
            "ROUTE_LOOKUP_INPUT",
            extra={"extra_data": {"route_identifier": route_identifier}}
        )
        
        # Step 1 — exact match on route_id
        route = db.query(Route).filter(
            Route.route_id == str(route_identifier)
        ).first()
        
        if route:
            app_logger.info(
                "ROUTE_LOOKUP_TYPE",
                extra={"extra_data": {"lookup_type": "route_id", "route_identifier": route_identifier}}
            )
            app_logger.info(
                "ROUTE_LOOKUP_RESULT",
                extra={"extra_data": {
                    "found": True,
                    "route_id": route.route_id,
                    "route_short_name": getattr(route, 'route_short_name', None),
                    "route_long_name": getattr(route, 'route_long_name', None),
                }}
            )
            return route
        
        # Step 2 — case-insensitive match on route_short_name
        route = db.query(Route).filter(
            Route.route_short_name.ilike(str(route_identifier))
        ).first()
        
        if route:
            app_logger.info(
                "ROUTE_LOOKUP_TYPE",
                extra={"extra_data": {"lookup_type": "route_short_name", "route_identifier": route_identifier}}
            )
            app_logger.info(
                "ROUTE_LOOKUP_RESULT",
                extra={"extra_data": {
                    "found": True,
                    "route_id": route.route_id,
                    "route_short_name": getattr(route, 'route_short_name', None),
                    "route_long_name": getattr(route, 'route_long_name', None),
                }}
            )
            return route
        
        # Not found
        app_logger.info(
            "ROUTE_LOOKUP_RESULT",
            extra={"extra_data": {"found": False, "route_identifier": route_identifier}}
        )
        return None

    def _resolve_stop_id(self, stop_name: str, db: Session) -> Optional[str]:
        """Resolve stop name to stop ID using database lookup with fuzzy word matching."""
        try:
            # 1. Try full phrase match first (fastest)
            stop = db.query(GTFSStop).filter(
                GTFSStop.stop_name.ilike(f"%{stop_name}%")
            ).first()
            if stop:
                return stop.stop_id
            
            # 2. Word-by-word scoring: find stop whose name contains the most query words
            # This handles spelling variants like "nagarbhavi" vs "Nagarabhavi"
            words = [w for w in stop_name.lower().split() if len(w) > 2]
            if not words:
                return None
            
            best_stop = None
            best_score = 0
            
            # Query candidates that contain at least the first significant word
            for word in words:
                candidates = db.query(GTFSStop).filter(
                    GTFSStop.stop_name.ilike(f"%{word}%")
                ).all()
                for candidate in candidates:
                    name_lower = candidate.stop_name.lower()
                    score = sum(1 for w in words if w in name_lower)
                    if score > best_score:
                        best_score = score
                        best_stop = candidate
            
            if best_stop and best_score >= max(1, len(words) // 2):
                app_logger.info(f"Fuzzy matched '{stop_name}' -> '{best_stop.stop_name}' (score={best_score}/{len(words)})")
                return best_stop.stop_id
            
            return None
        except Exception as e:
            app_logger.error(f"Error resolving stop ID for {stop_name}: {e}")
            return None
    
    async def _get_route_info(self, parameters: Dict[str, Any], session_id: str, db: Session = None) -> Dict[str, Any]:
        """Get information about a specific transit route.
        
        Supports both numeric route_id (e.g. '2872') and public route_short_name
        (e.g. '500-LA', '600-A', '244-C VSD').
        """
        route_identifier = parameters.get('route_id') or parameters.get('route_short_name')
        
        if not route_identifier:
            return {
                "success": False,
                "error": "No route identifier provided",
                "message": "Please tell me which route number you'd like information about."
            }
        
        db = next(get_db())
        try:
            route = self._resolve_route(route_identifier, db)
            
            if not route:
                return {
                    "success": False,
                    "error": f"Route '{route_identifier}' not found",
                    "message": f"I couldn't find route {route_identifier}. Please check the route number and try again."
                }
            
            route_type_raw = getattr(route, 'route_type', None) or getattr(route, 'type', None)
            # GTFS route_type codes: 0=Tram, 1=Metro, 2=Rail, 3=Bus, 700=Bus
            type_map = {0: "Tram", 1: "Metro", 2: "Rail", 3: "Bus", 700: "Bus", 800: "Trolleybus"}
            if isinstance(route_type_raw, int):
                route_type_str = type_map.get(route_type_raw, f"Type {route_type_raw}")
            elif route_type_raw:
                route_type_str = str(route_type_raw)
            else:
                route_type_str = "Bus"
            
            return {
                "success": True,
                "route_id": route.route_id,
                "route_short_name": getattr(route, 'route_short_name', route_identifier),
                "route_long_name": getattr(route, 'route_long_name', 'N/A'),
                "route_type": route_type_str,
            }
        except Exception as e:
            app_logger.error(f"Error looking up route '{route_identifier}': {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"I encountered an error looking up route {route_identifier}. Please try again."
            }
    
    async def format_response(self, tool_call: ToolCall, query: str) -> str:
        """Format the tool result into a passenger-friendly response using LLM."""
        if not tool_call.success:
            return tool_call.result.get('message', tool_call.error) if tool_call.result else tool_call.error
        
        result = tool_call.result
        
        # Try to generate natural response using LLM
        natural_response = await self._generate_natural_response(tool_call.tool_name, tool_call.parameters, result, query)
        if natural_response:
            return natural_response
        
        # Fallback to templates if LLM fails
        if tool_call.tool_name == "plan_trip":
            return self._format_journey_response(result)
        elif tool_call.tool_name == "get_alternative_routes":
            return self._format_alternatives_response(result)
        elif tool_call.tool_name == "get_crowd_info":
            return self._format_crowd_response(result)
        elif tool_call.tool_name == "get_service_info":
            return self._format_service_response(result)
        elif tool_call.tool_name == "get_travel_time":
            return self._format_travel_time_response(result)
        elif tool_call.tool_name == "get_route_info":
            return self._format_route_info_response(result)
        elif tool_call.tool_name == "get_demand_insights":
            return self._format_demand_insights_response(result)
        elif tool_call.tool_name == "get_busiest_routes":
            return self._format_busiest_routes_response(result)
        elif tool_call.tool_name == "get_fleet_recommendations":
            return self._format_fleet_recommendations_response(result)
        else:
            return "I've processed your request. Let me get that information for you."

    async def _generate_natural_response(self, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any], query: str) -> Optional[str]:
        """Generate a natural conversational response using Groq."""
        if not self.api_key:
            return None
            
        system_prompt = """You are an AI Transit Assistant. Your job is to rewrite structured backend transit data into a conversational, human-friendly response for a passenger.
CRITICAL RULES:
1. Do NOT invent, estimate, or hallucinate any numbers or facts. Only use the provided data.
2. Keep it concise, helpful, and polite.
3. If the data is empty or missing, state that clearly.
"""
        # Extract minimal structured data to avoid token bloat
        minimal_result = {k: v for k, v in result.items() if k not in ["success", "message", "error"]}
        
        user_message = f"User Query: {query}\n\nTool Executed: {tool_name}\n\nBackend Data: {json.dumps(minimal_result)}\n\nPlease provide a natural response based ONLY on this backend data."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.groq_model,
                "messages": messages,
                "temperature": 0.3
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                content = response.json()['choices'][0]['message']['content']
                return content.strip()
        except Exception as e:
            app_logger.error(f"Error generating natural response: {e}")
            return None
    
    def _format_journey_response(self, result: Dict[str, Any]) -> str:
        """Format journey planning result."""
        if not result.get('success'):
            return result.get('message', "I couldn't plan your journey. Please try again.")
        
        route_id = result.get('route_id', 'Unknown')
        eta = result.get('eta_minutes', 0)
        distance = result.get('distance_km', 0)
        transfers = result.get('transfers', 0)
        
        response = f"I found a route for you! "
        response += f"Route {route_id} will take approximately {eta} minutes "
        response += f"and covers {distance} km. "
        
        if transfers == 0:
            response += "This is a direct route with no transfers. "
        else:
            response += f"This route has {transfers} transfer(s). "
        
        response += "Would you like me to show you alternative routes?"
        
        return response

    def _format_demand_insights_response(self, result: Dict[str, Any]) -> str:
        """Format demand insights result."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve demand insights.")
        summary = result.get('summary', {})
        avg_demand = summary.get('average_passenger_count', 0)
        highest_route = summary.get('highest_demand_route', 'N/A')
        return f"Currently, the average passenger demand is {avg_demand} per route. Route {highest_route} is experiencing the highest demand."

    def _format_busiest_routes_response(self, result: Dict[str, Any]) -> str:
        """Format busiest routes result."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve the busiest routes.")
        top_routes = result.get('top_routes', [])
        if not top_routes:
            return "There is no demand data available right now."
        response = "Here are the busiest routes right now:\n"
        for i, route in enumerate(top_routes, 1):
            response += f"{i}. Route {route.get('route_id')} (Avg Passengers: {route.get('average_passenger_count')})\n"
        return response

    def _format_fleet_recommendations_response(self, result: Dict[str, Any]) -> str:
        """Format fleet recommendations result."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve fleet recommendations.")
        recs = result.get('recommendations', {})
        breakdown = recs.get('per_route_breakdown', [])
        if not breakdown:
            return "No fleet recommendations available at the moment."
        response = "Here are the latest fleet optimization recommendations:\n"
        for route in breakdown[:5]:
            status = route.get('status')
            gap = route.get('fleet_gap')
            if status == "shortage":
                response += f"- Route {route.get('route_id')}: Needs {gap} more bus(es) due to high demand.\n"
            elif status == "surplus":
                response += f"- Route {route.get('route_id')}: Has a surplus of {abs(gap)} bus(es).\n"
            else:
                response += f"- Route {route.get('route_id')}: Fleet allocation is sufficient.\n"
        return response
    
    def _format_crowd_response(self, result: Dict[str, Any]) -> str:
        """Format crowd level response with passenger-friendly language."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve crowd information. Please try again.")
        
        crowd_level = result.get('crowd_level', 'Unknown')
        
        if crowd_level == "Very Comfortable":
            return "This route is currently less crowded. You should have a comfortable journey with plenty of space."
        elif crowd_level == "Comfortable":
            return "This route is comfortable. You should be able to find a seat easily."
        elif crowd_level == "Moderately Busy":
            return "This route is moderately busy. It may be a bit crowded during peak hours, but you should still find seating."
        elif crowd_level == "Busy":
            return "This route is expected to be busy. You may need to stand during peak periods."
        elif crowd_level == "Very Crowded":
            return "This route is very crowded. Expect limited space and standing passengers."
        else:
            return "I don't have specific crowd information for this route right now."
    
    def _format_service_response(self, result: Dict[str, Any]) -> str:
        """Format service information response with passenger-friendly language."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve service information. Please try again.")
        
        service_level = result.get('service_level', 'Unknown')
        headway_minutes = result.get('headway_minutes', 0)
        
        if service_level == "Limited Service":
            return "Bus service may be less frequent on this route. Please check the schedule and plan accordingly."
        elif service_level == "Regular Service":
            return "Regular bus service is available on this route."
        elif service_level == "Frequent Service":
            return "Frequent bus service is available on this route. Buses run regularly."
        elif service_level == "Very Frequent Service":
            return "Very frequent bus service is available on this route. You won't have to wait long."
        else:
            return "I don't have specific service frequency information for this route right now."
    
    def _format_travel_time_response(self, result: Dict[str, Any]) -> str:
        """Format travel time response with passenger-friendly language."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve travel time information. Please try again.")
        
        eta_minutes = result.get('eta_minutes', 0)
        distance_km = result.get('distance_km', 0)
        transfers = result.get('transfers', 0)
        
        response = f"This journey will take approximately {eta_minutes} minutes "
        response += f"and covers {distance_km} km. "
        
        if transfers == 0:
            response += "This is a direct route with no transfers required."
        elif transfers == 1:
            response += "This route requires 1 transfer."
        else:
            response += f"This route requires {transfers} transfers."
        
        return response
    
    def _format_alternatives_response(self, result: Dict[str, Any]) -> str:
        """Format alternative routes result."""
        alternatives = result.get('alternative_routes', [])
        
        if not alternatives:
            return "I couldn't find any alternative routes for this journey."
        
        response = f"I found {len(alternatives)} alternative route(s):\n\n"
        
        for i, alt in enumerate(alternatives, 1):
            strategy = alt.get('strategy', 'Unknown')
            eta = alt.get('eta', 0)
            distance = alt.get('distance', 0)
            transfers = alt.get('transfers', 0)
            
            response += f"{i}. {strategy}: {eta} min, {distance} km, {transfers} transfer(s)\n"
        
        return response
    
    def _format_route_info_response(self, result: Dict[str, Any]) -> str:
        """Format route information response."""
        if not result.get('success'):
            return result.get('message', "I couldn't retrieve route information. Please try again.")
        
        route_id = result.get('route_id', 'Unknown')
        short_name = result.get('route_short_name', route_id)
        long_name = result.get('route_long_name', '')
        route_type = result.get('route_type', 'Bus')
        
        response = f"Route {short_name}"
        if long_name and long_name != 'N/A':
            response += f" ({long_name})"
        response += f" is a {route_type} service."
        response += " Would you like to plan a journey on this route, or get crowd and timing information?"
        return response
    
    def clear_context(self, session_id: str):
        """Clear conversation context for a session."""
        if session_id in self.conversation_contexts:
            del self.conversation_contexts[session_id]


# Global service instance
ai_assistant_service = AIAssistantService()
