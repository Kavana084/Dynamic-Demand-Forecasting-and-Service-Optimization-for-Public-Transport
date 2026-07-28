import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.exceptions import (
    ServiceException,
    validation_exception_handler,
    service_exception_handler,
    unexpected_exception_handler
)
from fastapi import Request
import json

class MockRequest:
    pass

async def run_tests():
    req = MockRequest()
    
    print("--- Testing Validation Error ---")
    exc1 = RequestValidationError(errors=[{"loc": ("body", "route_id"), "msg": "field required", "type": "value_error.missing"}])
    resp1 = await validation_exception_handler(req, exc1)
    print(f"Status Code: {resp1.status_code}")
    print(f"Response JSON: {resp1.body.decode('utf-8')}")
    
    print("\n--- Testing ServiceException ---")
    exc2 = ServiceException("This is a simulated service error", error_code="SIMULATED_SERVICE_ERROR")
    resp2 = await service_exception_handler(req, exc2)
    print(f"Status Code: {resp2.status_code}")
    print(f"Response JSON: {resp2.body.decode('utf-8')}")
    
    print("\n--- Testing Unexpected Exception ---")
    exc3 = Exception("This is a simulated unexpected exception")
    resp3 = await unexpected_exception_handler(req, exc3)
    print(f"Status Code: {resp3.status_code}")
    print(f"Response JSON: {resp3.body.decode('utf-8')}")

    print("\n--- Verifying Logs Directory ---")
    log_path = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
    if os.path.exists(log_path):
        print(f"Log file exists at {log_path}")
        with open(log_path, 'r') as f:
            print("Last 2 log lines:")
            lines = f.readlines()
            for line in lines[-2:]:
                print(line.strip())
    else:
        print(f"Log file NOT found at {log_path}")

asyncio.run(run_tests())
