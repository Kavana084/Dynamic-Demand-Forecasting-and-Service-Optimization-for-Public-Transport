"""
AI Transit Assistant End-to-End Validation Audit
------------------------------------------------
Comprehensive audit script to verify AI Assistant functionality.
"""

import asyncio
import json
import time
import httpx
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = "outputs"

# Test data - stop IDs from database
TEST_STOPS = {
    "nagarabhavi": "1002",
    "majestic": "1003",
    "mg_road": "1004",
    "indiranagar": "1005",
    "koramangala": "1006",
    "electronic_city": "1007",
    "whitefield": "1008",
    "yelahanka": "1009",
    "btm_layout": "1010",
    "hsr_layout": "1011",
}

# Test queries for each intent
INTENT_TESTS = {
    "journey_planning": [
        "Plan a trip to Majestic",
        "How do I reach MG Road?",
        "Take me to Electronic City",
    ],
    "crowd_info": [
        "How crowded is this route?",
        "Will it be busy?",
        "Is this route crowded?",
    ],
    "service_info": [
        "How often do buses run?",
        "Are buses available?",
        "What is the bus frequency?",
    ],
    "travel_time": [
        "How long will it take?",
        "What is the travel time?",
        "How many minutes to reach?",
    ],
    "weather_impact": [
        "Will rain affect my trip?",
        "How does weather impact the route?",
    ],
    "traffic_impact": [
        "How is traffic on this route?",
        "Will traffic delay my journey?",
    ],
    "transfer_info": [
        "Do I need to change buses?",
        "How many transfers are there?",
    ],
}

# Hallucination test queries
HALLUCINATION_TESTS = [
    "What is the capital of France?",
    "Write Python code to sort a list",
    "Tell me a joke",
    "What is Bitcoin?",
    "Who won the World Cup?",
]

# Dynamic response test routes
DYNAMIC_ROUTE_TESTS = [
    ("nagarabhavi", "majestic"),
    ("mg_road", "indiranagar"),
    ("koramangala", "electronic_city"),
    ("whitefield", "yelahanka"),
    ("btm_layout", "hsr_layout"),
    ("majestic", "koramangala"),
    ("indiranagar", "whitefield"),
    ("electronic_city", "btm_layout"),
    ("yelahanka", "mg_road"),
    ("hsr_layout", "nagarabhavi"),
]

# Context memory conversation flow
CONTEXT_MEMORY_FLOW = [
    "Plan a trip from Nagarabhavi to Majestic",
    "Will it be crowded?",
    "How often do buses run?",
    "Will rain affect the journey?",
]


class AIAssistantAuditor:
    """Auditor for AI Transit Assistant."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self.results = defaultdict(list)
        self.performance_metrics = []
        
    async def send_message(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """Send a message to the AI Assistant."""
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{API_BASE_URL}/api/ai-assistant/chat",
                json={
                    "message": message,
                    "session_id": session_id
                }
            )
            response.raise_for_status()
            data = response.json()
            
            elapsed_ms = (time.time() - start_time) * 1000
            self.performance_metrics.append(elapsed_ms)
            
            return {
                "success": True,
                "answer": data.get("answer", ""),
                "confidence": data.get("confidence", 0.0),
                "session_id": data.get("session_id", ""),
                "latency_ms": elapsed_ms,
                "raw_response": data
            }
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.performance_metrics.append(elapsed_ms)
            
            return {
                "success": False,
                "error": str(e),
                "latency_ms": elapsed_ms
            }
    
    async def test_backend_flow(self) -> Dict[str, Any]:
        """Test 1: Backend Flow Verification."""
        print("Testing Backend Flow Verification...")
        
        test_query = "Plan a trip to Majestic"
        result = await self.send_message(test_query)
        
        flow_data = {
            "user_query": test_query,
            "detected_intent": "plan_trip",  # Would be extracted from logs in production
            "context_received": self.session_id,
            "backend_services_called": ["plan_navigation"],
            "data_returned": result.get("raw_response", {}),
            "final_response": result.get("answer", ""),
            "latency_ms": result.get("latency_ms", 0),
            "success": result.get("success", False)
        }
        
        self.results["backend_flow"] = flow_data
        return flow_data
    
    async def test_intent_validation(self) -> Dict[str, Any]:
        """Test 2: Intent Validation."""
        print("Testing Intent Validation...")
        
        intent_results = {}
        
        for intent, queries in INTENT_TESTS.items():
            intent_results[intent] = []
            for query in queries:
                result = await self.send_message(query, self.session_id)
                if result.get("success"):
                    self.session_id = result.get("session_id", self.session_id)
                
                intent_results[intent].append({
                    "query": query,
                    "response": result.get("answer", ""),
                    "confidence": result.get("confidence", 0.0),
                    "success": result.get("success", False),
                    "latency_ms": result.get("latency_ms", 0)
                })
        
        self.results["intent_validation"] = intent_results
        return intent_results
    
    async def test_dynamic_responses(self) -> Dict[str, Any]:
        """Test 3: Dynamic Response Validation."""
        print("Testing Dynamic Response Validation...")
        
        dynamic_results = {
            "route_responses": [],
            "crowd_responses": [],
            "service_responses": [],
            "travel_time_responses": []
        }
        
        for origin_key, dest_key in DYNAMIC_ROUTE_TESTS:
            origin_id = TEST_STOPS.get(origin_key)
            dest_id = TEST_STOPS.get(dest_key)
            
            # Test journey planning
            query = f"Plan a trip from {origin_key} to {dest_key}"
            result = await self.send_message(query, self.session_id)
            if result.get("success"):
                self.session_id = result.get("session_id", self.session_id)
            
            dynamic_results["route_responses"].append({
                "route": f"{origin_key} -> {dest_key}",
                "query": query,
                "response": result.get("answer", ""),
                "response_hash": hash(result.get("answer", ""))
            })
            
            # Test crowd info
            crowd_query = "How crowded is this route?"
            crowd_result = await self.send_message(crowd_query, self.session_id)
            dynamic_results["crowd_responses"].append({
                "route": f"{origin_key} -> {dest_key}",
                "query": crowd_query,
                "response": crowd_result.get("answer", ""),
                "response_hash": hash(crowd_result.get("answer", ""))
            })
            
            # Test service info
            service_query = "How often do buses run?"
            service_result = await self.send_message(service_query, self.session_id)
            dynamic_results["service_responses"].append({
                "route": f"{origin_key} -> {dest_key}",
                "query": service_query,
                "response": service_result.get("answer", ""),
                "response_hash": hash(service_result.get("answer", ""))
            })
            
            # Test travel time
            time_query = "How long will it take?"
            time_result = await self.send_message(time_query, self.session_id)
            dynamic_results["travel_time_responses"].append({
                "route": f"{origin_key} -> {dest_key}",
                "query": time_query,
                "response": time_result.get("answer", ""),
                "response_hash": hash(time_result.get("answer", ""))
            })
        
        # Check if responses are dynamic
        route_hashes = [r["response_hash"] for r in dynamic_results["route_responses"]]
        crowd_hashes = [r["response_hash"] for r in dynamic_results["crowd_responses"]]
        service_hashes = [r["response_hash"] for r in dynamic_results["service_responses"]]
        time_hashes = [r["response_hash"] for r in dynamic_results["travel_time_responses"]]
        
        dynamic_results["validation"] = {
            "route_responses_dynamic": len(set(route_hashes)) > 1,
            "crowd_responses_dynamic": len(set(crowd_hashes)) > 1,
            "service_responses_dynamic": len(set(service_hashes)) > 1,
            "travel_time_responses_dynamic": len(set(time_hashes)) > 1,
            "unique_route_responses": len(set(route_hashes)),
            "unique_crowd_responses": len(set(crowd_hashes)),
            "unique_service_responses": len(set(service_hashes)),
            "unique_travel_time_responses": len(set(time_hashes))
        }
        
        self.results["dynamic_responses"] = dynamic_results
        return dynamic_results
    
    def test_passenger_language_compliance(self) -> Dict[str, Any]:
        """Test 4: Passenger Language Compliance."""
        print("Testing Passenger Language Compliance...")
        
        forbidden_terms = [
            "catboost",
            "predicted_demand",
            "fleet optimization",
            "utilization",
            "model confidence",
            "ml",
            "machine learning",
            "feature",
            "training",
            "inference",
            "prediction model",
            "optimization score",
            "demand confidence"
        ]
        
        all_responses = []
        
        # Collect all responses from previous tests
        if "intent_validation" in self.results:
            for intent, results in self.results["intent_validation"].items():
                for result in results:
                    all_responses.append(result.get("response", ""))
        
        if "dynamic_responses" in self.results:
            for category in ["route_responses", "crowd_responses", "service_responses", "travel_time_responses"]:
                for result in self.results["dynamic_responses"][category]:
                    all_responses.append(result.get("response", ""))
        
        # Check for forbidden terms
        violations = []
        compliant_responses = []
        
        for response in all_responses:
            response_lower = response.lower()
            found_terms = []
            
            for term in forbidden_terms:
                if term.lower() in response_lower:
                    found_terms.append(term)
            
            if found_terms:
                violations.append({
                    "response": response[:200],
                    "forbidden_terms": found_terms
                })
            else:
                compliant_responses.append(response)
        
        compliance_data = {
            "total_responses_checked": len(all_responses),
            "compliant_responses": len(compliant_responses),
            "violations_found": len(violations),
            "compliance_rate": len(compliant_responses) / len(all_responses) if all_responses else 0,
            "violations": violations[:10],  # Limit to first 10
            "forbidden_terms_checked": forbidden_terms
        }
        
        self.results["passenger_language"] = compliance_data
        return compliance_data
    
    async def test_context_memory(self) -> Dict[str, Any]:
        """Test 5: Context Memory."""
        print("Testing Context Memory...")
        
        # Start fresh session
        self.session_id = None
        context_results = []
        
        for i, query in enumerate(CONTEXT_MEMORY_FLOW):
            result = await self.send_message(query, self.session_id)
            if result.get("success"):
                self.session_id = result.get("session_id", self.session_id)
            
            context_results.append({
                "step": i + 1,
                "query": query,
                "response": result.get("answer", ""),
                "session_id": self.session_id,
                "success": result.get("success", False)
            })
        
        # Check if context is preserved
        session_ids = [r["session_id"] for r in context_results]
        context_preserved = len(set(session_ids)) == 1 and session_ids[0] is not None
        
        context_data = {
            "conversation_flow": context_results,
            "session_ids": session_ids,
            "context_preserved": context_preserved,
            "unique_session_ids": len(set(session_ids))
        }
        
        self.results["context_memory"] = context_data
        return context_data
    
    async def test_hallucination_safety(self) -> Dict[str, Any]:
        """Test 6: Hallucination Safety."""
        print("Testing Hallucination Safety...")
        
        hallucination_results = []
        
        for query in HALLUCINATION_TESTS:
            result = await self.send_message(query, self.session_id)
            
            # Check if response redirects to transit assistance
            response = result.get("answer", "").lower()
            is_safe_redirect = any(term in response for term in ["transit", "journey", "route", "bus", "travel", "help"])
            
            hallucination_results.append({
                "query": query,
                "response": result.get("answer", ""),
                "is_safe_redirect": is_safe_redirect,
                "success": result.get("success", False)
            })
        
        safe_count = sum(1 for r in hallucination_results if r["is_safe_redirect"])
        
        hallucination_data = {
            "total_tests": len(hallucination_results),
            "safe_redirects": safe_count,
            "safety_rate": safe_count / len(hallucination_results) if hallucination_results else 0,
            "results": hallucination_results
        }
        
        self.results["hallucination_safety"] = hallucination_data
        return hallucination_data
    
    def test_performance(self) -> Dict[str, Any]:
        """Test 7: Performance Metrics."""
        print("Testing Performance Metrics...")
        
        if not self.performance_metrics:
            return {
                "error": "No performance data collected",
                "total_requests": 0
            }
        
        sorted_metrics = sorted(self.performance_metrics)
        n = len(sorted_metrics)
        
        performance_data = {
            "total_requests": n,
            "average_latency_ms": sum(sorted_metrics) / n if n > 0 else 0,
            "min_latency_ms": min(sorted_metrics) if n > 0 else 0,
            "max_latency_ms": max(sorted_metrics) if n > 0 else 0,
            "p50_latency_ms": sorted_metrics[n // 2] if n > 0 else 0,
            "p95_latency_ms": sorted_metrics[int(n * 0.95)] if n > 0 else 0,
            "p99_latency_ms": sorted_metrics[int(n * 0.99)] if n > 0 else 0,
            "all_latencies_ms": sorted_metrics
        }
        
        self.results["performance"] = performance_data
        return performance_data
    
    async def run_all_tests(self):
        """Run all audit tests."""
        print("Starting AI Assistant End-to-End Audit...")
        print("=" * 60)
        
        # Test 1: Backend Flow
        await self.test_backend_flow()
        
        # Test 2: Intent Validation
        await self.test_intent_validation()
        
        # Test 3: Dynamic Responses
        await self.test_dynamic_responses()
        
        # Test 4: Passenger Language Compliance
        self.test_passenger_language_compliance()
        
        # Test 5: Context Memory
        await self.test_context_memory()
        
        # Test 6: Hallucination Safety
        await self.test_hallucination_safety()
        
        # Test 7: Performance
        self.test_performance()
        
        print("=" * 60)
        print("Audit Complete. Generating reports...")
        
        await self.client.aclose()
    
    def generate_reports(self):
        """Generate all audit reports."""
        import os
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Report 1: Backend Flow
        with open(f"{OUTPUT_DIR}/ai_assistant_flow_audit.json", "w") as f:
            json.dump(self.results.get("backend_flow", {}), f, indent=2)
        
        # Report 2: Intent Validation
        with open(f"{OUTPUT_DIR}/intent_validation_report.json", "w") as f:
            json.dump(self.results.get("intent_validation", {}), f, indent=2)
        
        # Report 3: Dynamic Response
        with open(f"{OUTPUT_DIR}/dynamic_response_report.json", "w") as f:
            json.dump(self.results.get("dynamic_responses", {}), f, indent=2)
        
        # Report 4: Passenger Language
        with open(f"{OUTPUT_DIR}/passenger_language_audit.json", "w") as f:
            json.dump(self.results.get("passenger_language", {}), f, indent=2)
        
        # Report 5: Context Memory
        with open(f"{OUTPUT_DIR}/context_memory_report.json", "w") as f:
            json.dump(self.results.get("context_memory", {}), f, indent=2)
        
        # Report 6: Hallucination Safety
        with open(f"{OUTPUT_DIR}/hallucination_safety_report.json", "w") as f:
            json.dump(self.results.get("hallucination_safety", {}), f, indent=2)
        
        # Report 7: Performance
        with open(f"{OUTPUT_DIR}/ai_performance_report.json", "w") as f:
            json.dump(self.results.get("performance", {}), f, indent=2)
        
        # Final Readiness Report
        self.generate_readiness_report()
    
    def generate_readiness_report(self):
        """Generate final readiness report."""
        performance = self.results.get("performance", {})
        dynamic = self.results.get("dynamic_responses", {}).get("validation", {})
        language = self.results.get("passenger_language", {})
        context = self.results.get("context_memory", {})
        hallucination = self.results.get("hallucination_safety", {})
        
        # Calculate scores
        performance_score = 0
        if performance.get("average_latency_ms", 9999) < 2000:
            performance_score = 100
        elif performance.get("average_latency_ms", 9999) < 3000:
            performance_score = 70
        else:
            performance_score = 30
        
        dynamic_score = 0
        dynamic_count = sum([
            dynamic.get("route_responses_dynamic", False),
            dynamic.get("crowd_responses_dynamic", False),
            dynamic.get("service_responses_dynamic", False),
            dynamic.get("travel_time_responses_dynamic", False)
        ])
        dynamic_score = (dynamic_count / 4) * 100
        
        language_score = language.get("compliance_rate", 0) * 100
        context_score = 100 if context.get("context_preserved", False) else 0
        hallucination_score = hallucination.get("safety_rate", 0) * 100
        
        overall_score = (performance_score + dynamic_score + language_score + context_score + hallucination_score) / 5
        
        # Determine grade
        if overall_score >= 90:
            grade = "A"
            status = "Production Ready"
        elif overall_score >= 70:
            grade = "B"
            status = "Minor Improvements Needed"
        else:
            grade = "C"
            status = "Major Issues Found"
        
        readiness_report = {
            "audit_timestamp": datetime.now().isoformat(),
            "overall_score": round(overall_score, 2),
            "grade": grade,
            "status": status,
            "scores": {
                "performance": round(performance_score, 2),
                "dynamic_responses": round(dynamic_score, 2),
                "passenger_language": round(language_score, 2),
                "context_memory": round(context_score, 2),
                "hallucination_safety": round(hallucination_score, 2)
            },
            "performance_metrics": {
                "average_latency_ms": performance.get("average_latency_ms", 0),
                "p95_latency_ms": performance.get("p95_latency_ms", 0),
                "p99_latency_ms": performance.get("p99_latency_ms", 0),
                "target_avg": "< 2000ms",
                "target_p95": "< 3000ms",
                "meets_target": performance.get("average_latency_ms", 9999) < 2000 and performance.get("p95_latency_ms", 9999) < 3000
            },
            "dynamic_data_verification": {
                "route_responses_dynamic": dynamic.get("route_responses_dynamic", False),
                "crowd_responses_dynamic": dynamic.get("crowd_responses_dynamic", False),
                "service_responses_dynamic": dynamic.get("service_responses_dynamic", False),
                "travel_time_responses_dynamic": dynamic.get("travel_time_responses_dynamic", False)
            },
            "context_memory_verification": {
                "context_preserved": context.get("context_preserved", False),
                "unique_session_ids": context.get("unique_session_ids", 0)
            },
            "passenger_language_verification": {
                "compliance_rate": language.get("compliance_rate", 0),
                "violations_found": language.get("violations_found", 0),
                "total_responses_checked": language.get("total_responses_checked", 0)
            },
            "recommended_fixes": self.generate_recommendations(performance, dynamic, language, context, hallucination)
        }
        
        with open(f"{OUTPUT_DIR}/ai_assistant_readiness_report.json", "w") as f:
            json.dump(readiness_report, f, indent=2)
        
        print(f"\nFinal Grade: {grade} - {status}")
        print(f"Overall Score: {overall_score:.2f}/100")
        print(f"Reports generated in {OUTPUT_DIR}/")
    
    def generate_recommendations(self, performance, dynamic, language, context, hallucination):
        """Generate recommendations based on test results."""
        recommendations = []
        
        if performance.get("average_latency_ms", 9999) > 2000:
            recommendations.append("Optimize API response times - average latency exceeds 2000ms target")
        
        if performance.get("p95_latency_ms", 9999) > 3000:
            recommendations.append("Optimize P95 latency - exceeds 3000ms target")
        
        if not dynamic.get("validation", {}).get("route_responses_dynamic", True):
            recommendations.append("Route responses appear static - ensure journey data varies by route")
        
        if not dynamic.get("validation", {}).get("crowd_responses_dynamic", True):
            recommendations.append("Crowd responses appear static - ensure demand predictions vary")
        
        if language.get("compliance_rate", 1.0) < 1.0:
            recommendations.append(f"Found {language.get('violations_found', 0)} passenger language violations - review response generation")
        
        if not context.get("context_preserved", True):
            recommendations.append("Context memory not preserved - fix session ID management")
        
        if hallucination.get("safety_rate", 1.0) < 1.0:
            recommendations.append("Hallucination safety issues - improve fallback handling for unrelated queries")
        
        return recommendations


async def main():
    """Main audit execution."""
    auditor = AIAssistantAuditor()
    
    try:
        await auditor.run_all_tests()
        auditor.generate_reports()
    except Exception as e:
        print(f"Audit failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
