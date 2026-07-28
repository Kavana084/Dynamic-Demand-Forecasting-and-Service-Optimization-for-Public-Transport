import urllib.request
import json
import random

stops = [
    "21630", "20568", "22890", "22891", "29393", "22896", "22897", "35595", "21446", "29407"
]

def test_routes():
    url = "http://127.0.0.1:8000/api/plan_trip"
    
    results = []
    
    for i in range(10):
        src = random.choice(stops)
        dst = random.choice([s for s in stops if s != src])
        
        data = {
            "source_id": src,
            "destination_id": dst,
            "time": "12:00",
            "optimize": True
        }
        
        try:
            req = urllib.request.Request(url, method="POST")
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(data).encode('utf-8')
            
            with urllib.request.urlopen(req) as response:
                body = json.loads(response.read().decode())
                
                print(f"[{i}] Full response body keys: {list(body.keys())}")
                if 'data' in body:
                    r = body['data']
                    if isinstance(r, list):
                        r = r[0]
                else:
                    r = body
                    if not body.get('success'):
                        print(f"Error for {src}->{dst}: {body.get('message')}")
                        continue
                    
                res = {
                    "source": src,
                    "destination": dst,
                    "predicted_demand": r.get("predicted_demand"),
                    "forecast_demand": r.get("forecast_demand"),
                    "current_fleet": r.get("current_fleet"),
                    "required_buses": r.get("required_buses"),
                    "recommended_fleet": r.get("recommended_fleet"),
                    "additional_buses": r.get("additional_buses"),
                }
                results.append(res)
        except Exception as e:
            if hasattr(e, 'read'):
                print(f"Failed with {e.code}: {e.read().decode()}")
            else:
                print(f"Hard failure: {str(e)}")
            
    print(f"{'Source':<10} {'Dest':<10} {'Pred':<5} {'Forc':<5} {'Curr':<5} {'Req':<5} {'Rec':<5} {'Add':<5}")
    print("-" * 70)
    for r in results:
        print(f"{r['source'][:9]:<10} {r['destination'][:9]:<10} {str(r['predicted_demand']):<5} {str(r['forecast_demand']):<5} {str(r['current_fleet']):<5} {str(r['required_buses']):<5} {str(r['recommended_fleet']):<5} {str(r['additional_buses']):<5}")

test_routes()
 