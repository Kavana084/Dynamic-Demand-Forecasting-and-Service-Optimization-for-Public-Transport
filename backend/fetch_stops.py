import urllib.request
import json

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/stops') as response:
        stops = json.loads(response.read().decode())
        print("FIRST 5 STOPS:")
        for s in stops[:5]:
            print(f"ID: {s['stop_id']}, Name: {s['stop_name']}")
        
        print("\nMAJESTIC STOPS:")
        for s in stops:
            if "Majestic" in s['stop_name']:
                print(f"ID: {s['stop_id']}, Name: {s['stop_name']}")
                
        print("\nJAYANAGAR STOPS:")
        for s in stops:
            if "Jayanagar" in s['stop_name']:
                print(f"ID: {s['stop_id']}, Name: {s['stop_name']}")
except Exception as e:
    print("Error:", e)
