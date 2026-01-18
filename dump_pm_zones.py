import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def dump_zones():
    # Updated URI from .env (no auth)
    uri = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(uri)
    db = client.sut_smart_bus
    collection = db.pm_zones
    
    print("Connecting to DB...")
    cursor = collection.find({})
    zones = await cursor.to_list(length=100)
    
    print(f"Found {len(zones)} zones.")
    for z in zones:
        print("--- ZONE ---")
        print(f"ID: {z.get('_id')}")
        print(f"Name: {z.get('name')}")
        print(f"Points: {z.get('points')}")
        print(f"Lat: {z.get('lat')}")
        print(f"Lon: {z.get('lon')}")
        print("------------")

if __name__ == "__main__":
    asyncio.run(dump_zones())
