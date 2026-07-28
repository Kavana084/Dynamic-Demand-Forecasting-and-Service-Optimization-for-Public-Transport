import requests

try:
    response = requests.post(
        "http://127.0.0.1:8000/api/plan_trip", 
        json={"source": "Majestic", "destination": "Whitefield"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
