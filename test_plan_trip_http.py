"""
HTTP test for /api/plan_trip to verify verification fields.
"""
import urllib.request
import json

url = "http://127.0.0.1:8000/api/plan_trip"
payload = json.dumps({"source_id": "21630", "destination_id": "20568"}).encode()

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

print("Sending POST to /api/plan_trip ...")
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = resp.read().decode()
    data = json.loads(body)

    # Extract just the verification fields
    verification = {
        "fare": data.get("fare"),
        "occupancy_percent": data.get("occupancy_percent"),
        "crowd_level": data.get("crowd_level"),
        "comfort_level": data.get("comfort_level"),
        "bus_id": data.get("bus_id"),
    }

    print("\n=== VERIFICATION FIELDS ===")
    print(json.dumps(verification, indent=2))
    print("\n=== FULL RESPONSE (first 3000 chars) ===")
    print(body[:3000])
except Exception as e:
    print(f"Error: {e}")
