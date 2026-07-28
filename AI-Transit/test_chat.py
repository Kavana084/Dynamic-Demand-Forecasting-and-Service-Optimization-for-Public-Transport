import urllib.request
import json

def test_endpoint(message):
    try:
        print(f"Testing message: {message}")
        req = urllib.request.Request(
            'http://localhost:8000/api/ai-assistant/chat',
            data=json.dumps({'message': message}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        res = urllib.request.urlopen(req)
        print("Response:", res.read().decode())
    except Exception as e:
        print('Error:', e)

test_endpoint('Explain quantum computing in one paragraph')
test_endpoint('plan journey from 12th block nagarbhavi to banashankari')
