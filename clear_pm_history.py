import motor.motor_asyncio
import asyncio

async def clear_history():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["sut_smart_bus"]
    result = await db["hardware_locations"].delete_many({})
    print(f"Cleared {result.deleted_count} documents from hardware_locations.")

if __name__ == "__main__":
    asyncio.run(clear_history())
