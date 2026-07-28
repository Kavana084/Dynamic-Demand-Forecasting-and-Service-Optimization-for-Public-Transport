import urllib.request
import json

url = 'http://localhost:8000/api/plan_trip'
data = json.dumps({'source_id': '21630', 'destination_id': '20623'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        route_path = res.get('route_path', [])
        stops = res.get('stops', [])
        total_stops = res.get('total_stops', 0)
        
        print(f'route_path.length: {len(route_path)}')
        print(f'stops.length: {len(stops)}')
        print(f'total_stops: {total_stops}')
        
        # Check for duplicates in route_path
        stop_ids = [s.get('stop_id') for s in route_path]
        print(f'Duplicate stop IDs in route_path: {len(stop_ids) != len(set(stop_ids))}')
        
        if len(stop_ids) != len(set(stop_ids)):
            import collections
            duplicates = [item for item, count in collections.Counter(stop_ids).items() if count > 1]
            print(f'Duplicate IDs: {duplicates}')
            
            for s in route_path:
                if s.get('stop_id') in duplicates:
                    print(s)
except Exception as e:
    print('Error:', e)
