from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

response = client.post(
    "/api/plan_trip_v2",
    json={"source": "Majestic", "destination": "Whitefield"}
)

print(response.status_code)
print(response.json())
