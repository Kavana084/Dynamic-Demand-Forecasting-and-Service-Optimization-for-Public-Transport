import urllib.request, json

url = 'http://127.0.0.1:8000/api/plan_trip'
data = {'source_id': '21630', 'destination_id': '20568', 'time': '12:00', 'optimize': True}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
req.add_header('Content-Type', 'application/json')
try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
        if 'data' in body:
            d = body['data']
            if isinstance(d, list): d = d[0]
            print('route_id:', d.get('route_id'), 'predicted_demand:', d.get('predicted_demand'))
        else:
            print('Error:', body)
except Exception as e:
    if hasattr(e, 'read'): print(e.read().decode())
    else: print(e)
