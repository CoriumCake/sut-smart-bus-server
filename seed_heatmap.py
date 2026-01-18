import asyncio
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# SUT Coordinates
CENTER_LAT = 14.8820
CENTER_LON = 102.0207

async def seed_heatmap():
    uri = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(uri)
    db = client.sut_smart_bus
    collection = db.hardware_locations
    
    print("Connecting to DB...")
    
    # Generate 500 points
    points = []
    for i in range(500):
        # random offset within ~1km
        lat_offset = random.uniform(-0.01, 0.01)
        lon_offset = random.uniform(-0.01, 0.01)
        
        # High PM cluster near Gate 1 (north-eastish?)
        if i < 100:
             pm2_5 = random.uniform(50, 150) # Red
        elif i < 300:
             pm2_5 = random.uniform(25, 50) # Yellow
        else:
             pm2_5 = random.uniform(0, 25) # Green
             
        points.append({
            "lat": CENTER_LAT + lat_offset,
            "lon": CENTER_LON + lon_offset,
            "pm2_5": pm2_5,
            "pm10": pm2_5 * 1.5,
            "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        })
        
    if points:
        await collection.insert_many(points)
        print(f"Inserted {len(points)} heatmap points.")

if __name__ == "__main__":
    asyncio.run(seed_heatmap())
