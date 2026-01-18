import requests
import json

try:
    r = requests.get("http://localhost:8000/api/pm-zones")
    data = r.json()
    if data and len(data) > 0:
        print("Keys in first item:", list(data[0].keys()))
        print("Points value:", data[0].get("points"))
    else:
        print("No data or empty list returned")
except Exception as e:
    print(e)
