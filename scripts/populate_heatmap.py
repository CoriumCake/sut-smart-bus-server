
import asyncio
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://root:example@mongo:27017")
DB_NAME = "sut_smart_bus"
COLLECTION_NAME = "hardware_locations"

# Bus Routes (SUT Campus approximate loop)
# Start: Gate 1 -> Tech Building -> Dorms -> Gate 2 -> Farm -> Gate 1
ROUTE_POINTS = [
    (14.8820, 102.0150), # Gate 1
    (14.8845, 102.0200), # Tech
    (14.8860, 102.0250), # Dorms
    (14.8840, 102.0300), # Gate 2
    (14.8800, 102.0280), # Farm
    (14.8790, 102.0220), # Sports
    (14.8820, 102.0150)  # Back to Gate 1
]

BUSES = [
    {"mac": "24:6F:28:B2:4D:34", "name": "Bus 1 (Blue)"},
    {"mac": "24:6F:28:A1:B2:C3", "name": "Bus 2 (Red)"},
    {"mac": "24:6F:28:D4:E5:F6", "name": "Bus 3 (Green)"}
]

def interpolate_points(p1, p2, steps=10):
    points = []
    lat1, lon1 = p1
    lat2, lon2 = p2
    for i in range(steps):
        t = i / steps
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t
        points.append((lat, lon))
    return points

async def populate_data():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print("Generating heatmap data...")
    
    docs = []
    start_time = datetime.utcnow() - timedelta(hours=24)
    
    # Generate route path
    full_path = []
    for i in range(len(ROUTE_POINTS) - 1):
        segment = interpolate_points(ROUTE_POINTS[i], ROUTE_POINTS[i+1], steps=20)
        full_path.extend(segment)
        
    # Simulate 3 buses running for 24 hours
    for bus in BUSES:
        print(f"Generating data for {bus['name']}...")
        current_time = start_time
        path_index = 0
        
        while current_time < datetime.utcnow():
            # Move bus
            lat, lon = full_path[path_index]
            path_index = (path_index + 1) % len(full_path)
            
            # Generate variable PM2.5 based on location (simulating pollution zones)
            # Tech area (index 20-40) has higher pollution
            base_pm = 15.0
            if 15 <= path_index <= 45:
                base_pm += random.uniform(10, 30) # High pollution zone
            else:
                base_pm += random.uniform(-5, 5)  # Normal variation
                
            pm25 = max(5.0, base_pm)
            
            doc = {
                "bus_mac": bus['mac'],
                "bus_name": bus['name'],
                "lat": lat + random.uniform(-0.0001, 0.0001), # GPS jitter
                "lon": lon + random.uniform(-0.0001, 0.0001),
                "pm2_5": pm25,
                "pm10": pm25 * 1.2,
                "temp": 28.0 + random.uniform(-2, 2),
                "hum": 60.0 + random.uniform(-10, 10),
                "timestamp": current_time,
                "created_at": current_time
            }
            docs.append(doc)
            
            # 1 minute intervals
            current_time += timedelta(minutes=5)
            
    if docs:
        await collection.insert_many(docs)
        print(f"Successfully inserted {len(docs)} records.")
    else:
        print("No data generated.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(populate_data())
