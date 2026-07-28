import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

ENDPOINTS = [
    {"method": "POST", "url": "/api/predict_demand", "json": {"route_id": "3447", "hour": 8, "weather": "clear", "traffic": "medium"}},
    {"method": "POST", "url": "/api/optimize_fleet", "json": {"bus_capacity": 50, "max_buses_per_route": 10}},
    {"method": "GET", "url": "/api/dashboard/summary"},
    {"method": "GET", "url": "/api/dashboard/heatmap"},
    {"method": "GET", "url": "/api/dashboard/utilization"},
    {"method": "GET", "url": "/api/dashboard/forecast_trend/3447"},
    {"method": "GET", "url": "/api/health"},
]

def run_tests():
    print("="*50)
    print("Backend Validation Report")
    print("="*50)
    
    all_passed = True
    results = []
    
    for ep in ENDPOINTS:
        method = ep["method"]
        url = BASE_URL + ep["url"]
        payload = ep.get("json", None)
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, timeout=15)
            else:
                response = requests.post(url, json=payload, timeout=15)
                
            elapsed = time.time() - start_time
            status_code = response.status_code
            
            if status_code == 200:
                print(f"[{status_code}] {method} {ep['url']} - {elapsed:.3f}s -> PASS")
                results.append((ep['url'], "PASS", status_code, elapsed))
            else:
                print(f"[{status_code}] {method} {ep['url']} - {elapsed:.3f}s -> FAIL")
                print(f"Response: {response.text}")
                results.append((ep['url'], "FAIL", status_code, elapsed))
                all_passed = False
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[ERR] {method} {ep['url']} - {elapsed:.3f}s -> FAIL ({e})")
            results.append((ep['url'], "FAIL", "ERR", elapsed))
            all_passed = False
            
    print("\nSummary:")
    for url, status, code, duration in results:
        print(f"{url.ljust(35)} : {status}")

    if all_passed:
        print("\nAll endpoints tested successfully!")
        sys.exit(0)
    else:
        print("\nSome endpoints failed.")
        sys.exit(1)

if __name__ == "__main__":
    # Wait for server to be up
    try:
        requests.get(BASE_URL)
    except:
        print(f"Server is not running at {BASE_URL}. Please start Uvicorn first.")
        sys.exit(1)
        
    run_tests()
