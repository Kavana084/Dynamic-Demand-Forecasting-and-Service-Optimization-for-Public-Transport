import sys
import os
import time
import threading
import uvicorn
import urllib.request
import urllib.error
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.main import app
from app.exceptions import ServiceException

@app.get("/test_unexpected")
def test_unexpected():
    raise Exception("This is a simulated unexpected exception")

@app.get("/test_service_error")
def test_service_error():
    raise ServiceException("This is a simulated service error", error_code="SIMULATED_SERVICE_ERROR")

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

# Start server in background
thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(2)  # Give server time to start

def make_request(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        if data is not None:
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(data).encode('utf-8')
            
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 500, str(e)

print("--- Testing Validation Error ---")
status, response = make_request("http://127.0.0.1:8001/api/predict_demand", method="POST", data={})
print(f"Status Code: {status}")
print(f"Response JSON: {response}")

print("\n--- Testing ServiceException ---")
status, response = make_request("http://127.0.0.1:8001/test_service_error")
print(f"Status Code: {status}")
print(f"Response JSON: {response}")

print("\n--- Testing Unexpected Exception ---")
status, response = make_request("http://127.0.0.1:8001/test_unexpected")
print(f"Status Code: {status}")
print(f"Response JSON: {response}")

print("\n--- Verifying Logs Directory ---")
log_path = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
if os.path.exists(log_path):
    print(f"Log file exists at {log_path}")
    with open(log_path, 'r') as f:
        print("Last log line:")
        lines = f.readlines()
        if lines:
            print(lines[-1].strip())
else:
    print(f"Log file NOT found at {log_path}")

# Exit forcefully to kill daemon thread
os._exit(0)
