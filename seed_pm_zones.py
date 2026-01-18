import asyncio
import json
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Path to the shared JSON source of truth
JSON_PATH = "../sut-smart-bus-app/routes/pm_zones.json"

async def seed_zones():
    uri = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(uri)
    db = client.sut_smart_bus
    collection = db.pm_zones
    
    print("Connecting to DB...")
    
    # Check if file exists
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        static_zones = json.load(f)
        
    inserted_count = 0
    for zone in static_zones:
        # Prepare document for MongoDB
        # We don't save 'id' as 'id' usually, but we could save it as 'static_id' for ref?
        # Or just rely on 'name'.
        doc = {
            "name": zone["name"],
            "points": zone["points"],
            "avg_pm25": zone.get("avg_pm25", 0),
            "avg_pm10": 0, # Default
            # Add a flag to know these are system zones
            "is_static": True
        }
        
        # Check if exists by name to avoid dupes (though we just deleted all)
        existing = await collection.find_one({"name": zone["name"]})
        if not existing:
            await collection.insert_one(doc)
            inserted_count += 1
            print(f"Inserted: {zone['name']}")
        else:
            print(f"Skipped (Exists): {zone['name']}")
            
    print(f"Seed complete. Inserted {inserted_count} zones.")

if __name__ == "__main__":
    asyncio.run(seed_zones())
