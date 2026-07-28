import sys
sys.path.insert(0, 'f:/transit-ai-system/backend')
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)
response = client.post('/api/plan_trip', json={'source_id': 'stop_1', 'destination_id': 'stop_2'})
print(json.dumps(response.json(), indent=2))
