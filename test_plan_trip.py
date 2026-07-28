import requests
req = {'source_id': '101', 'destination_id': '205'}
try:
    res = requests.post('http://localhost:8000/api/plan_trip', json=req)
    print("Status Code:", res.status_code)
    import json
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print('Failed:', str(e))
