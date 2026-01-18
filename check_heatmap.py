import requests
import json

try:
    # URL might be localhost:8000
    r = requests.get("http://localhost:8000/api/heatmap?limit=10")
    if r.status_code == 200:
        data = r.json()
        print(f"Success! Received {len(data)} points.")
        if len(data) > 0:
            print("Sample point:", data[0])
    else:
        print(f"Error: {r.status_code} - {r.text}")
except Exception as e:
    print(f"Connection failed: {e}")
