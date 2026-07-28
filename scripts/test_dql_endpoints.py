import sys
import os
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from backend.app.main import app

client = TestClient(app)

def test_training():
    print("Testing /api/train_dql_model...")
    response = client.post("/api/train_dql_model", json={"episodes": 10})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_inference():
    print("Testing /api/predict_bus_allocation...")
    payload = {
        "predicted_demand": 80,
        "hour": 18,
        "weather": "rainy",
        "traffic": "high",
        "occupancy_rate": 0.72,
        "available_buses": 12
    }
    response = client.post("/api/predict_bus_allocation", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "recommended_buses" in response.json()

if __name__ == "__main__":
    test_training()
    test_inference()
    print("All tests passed.")
