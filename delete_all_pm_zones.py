import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def delete_all_zones():
    uri = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(uri)
    db = client.sut_smart_bus
    collection = db.pm_zones
    
    print("Connecting to DB...")
    
    # Delete all documents in the collection
    result = await collection.delete_many({})
    
    print(f"Deleted {result.deleted_count} zones.")

if __name__ == "__main__":
    asyncio.run(delete_all_zones())
