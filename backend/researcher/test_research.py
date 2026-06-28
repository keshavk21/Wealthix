import requests
import json

url = "http://localhost:8000/research"
payload = {
    "topic": "Apple stock outlook for 2024"
}

print(f"Sending POST request to {url} with payload:\n{json.dumps(payload, indent=2)}")

try:
    # 300 second timeout because the agent might take a while to search the web
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    
    print("\n✅ Success! Response:")
    print(json.dumps(response.json(), indent=2))
    
except requests.exceptions.RequestException as e:
    print(f"\n❌ Error connecting to server: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Server returned: {e.response.text}")
