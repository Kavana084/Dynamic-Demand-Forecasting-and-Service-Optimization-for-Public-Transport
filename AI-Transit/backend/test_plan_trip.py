import urllib.request
import json

def test_plan():
    url = "http://127.0.0.1:8000/api/plan_trip_v2"
    data = {
        "source": "Majestic",
        "destination": "Jayanagar",
        "time": "12:00",
        "optimize": True
    }
    
    try:
        req = urllib.request.Request(url, method="POST")
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
        
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = json.loads(response.read().decode())
            print(f"Success! Status: {status}")
            print(f"Response: {str(body)[:200]}...")
    except Exception as e:
        if hasattr(e, 'read'):
            print(f"Failed with {e.code}: {e.read().decode()}")
        else:
            print(f"Hard failure: {str(e)}")

test_plan()
