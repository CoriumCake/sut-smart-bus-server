
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://root:example@mongo:27017")
DB_NAME = "sut_smart_bus"
COLLECTION_NAME = "hardware_locations"

# The MAC addresses used in populate_heatmap.py
MOCK_MAC_ADDRESSES = [
    "24:6F:28:B2:4D:34", # Bus 1 (Blue)
    "24:6F:28:A1:B2:C3", # Bus 2 (Red)
    "24:6F:28:D4:E5:F6"  # Bus 3 (Green)
]

async def cleanup_data():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print("Cleaning up mock heatmap data...")
    
    result = await collection.delete_many({
        "bus_mac": {"$in": MOCK_MAC_ADDRESSES}
    })
    
    print(f"Deleted {result.deleted_count} records matching mock MAC addresses.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cleanup_data())
