import requests
import argparse
import time

# Configuration
SERVER_URL = "http://localhost:8000"
API_KEY = "your_api_key_here"  # Update this with your actual API key

def trigger_ota(device_type="esp32_cam", version="1.0.0", force=True):
    url = f"{SERVER_URL}/api/ota/trigger"
    
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
        
    data = {
        "device_type": device_type,
        "version": version,
        "force": force
    }
    
    print(f"🚀 Triggering OTA for {device_type} to v{version}...")
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            res = response.json()
            print(f"✅ Trigger success: {res['message']}")
            for r in res['payload']['results']:
                status = "✅" if r['success'] else "❌"
                print(f"   {status} Topic {r['topic']}")
            return True
        else:
            print(f"❌ Trigger failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trigger OTA Update (Push Only)')
    parser.add_argument('--version', type=str, required=True, help='Version string (e.g. 1.0.1)')
    parser.add_argument('--device', type=str, default="esp32_cam", help='Device type: esp32_cam or pm')
    
    args = parser.parse_args()
    
    # Confirm intent
    print(f"⚠️  This will trigger an OTA update for ALL {args.device} devices.")
    print(f"   Make sure 'firmware/{args.device}_{args.version}.bin' is already on the server.")
    
    trigger_ota(args.device, args.version, force=True)
