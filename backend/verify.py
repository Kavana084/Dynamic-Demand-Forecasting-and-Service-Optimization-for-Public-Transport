import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("--- Test 1: 'Majestic' -> 'Indiranagar' ---")
req1 = {"source": "Majestic", "destination": "Indiranagar"}
res1 = client.post("/api/plan_trip", json=req1)
print(f"Status: {res1.status_code}")
if res1.status_code == 200:
    data = res1.json()
    print(f"Source matched: {data['debug_metadata']['matched_source_stop']}")
    print(f"Source status: {data['debug_metadata']['normalization_status']['source']}")
else:
    print(res1.json())

print("\n--- Test 2: 'Witefield' -> 'Indiranagar' ---")
req2 = {"source": "Witefield", "destination": "Indiranagar"}
res2 = client.post("/api/plan_trip", json=req2)
print(f"Status: {res2.status_code}")
if res2.status_code == 200:
    data = res2.json()
    print(f"Source matched: {data['debug_metadata']['matched_source_stop']}")
    print(f"Source status: {data['debug_metadata']['normalization_status']['source']}")
else:
    print(res2.json())

print("\n--- Test 3: 'Koramanalaaa' -> 'Indiranagar' ---")
req3 = {"source": "Koramanalaaa", "destination": "Indiranagar"}
res3 = client.post("/api/plan_trip", json=req3)
print(f"Status: {res3.status_code}")
if res3.status_code == 400:
    print("400 Bad Request returned as expected.")
    print(res3.json())
else:
    print(f"Unexpected status: {res3.status_code}")
    print(res3.json())

print("\n--- Test 4: Determinism (10 identical requests) ---")
routes = []
for _ in range(10):
    res = client.post("/api/plan_trip", json={"source": "Majestic", "destination": "Whitefield"})
    if res.status_code == 200:
        routes.append(res.json()["route_id"])

print(f"Routes collected: {routes}")
if len(set(routes)) == 1:
    print("Determinism Verified: All 10 requests returned the identical route!")
else:
    print("Determinism Failed: Different routes returned.")
