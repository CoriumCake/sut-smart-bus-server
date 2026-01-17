from typing import List
from bson import ObjectId
from . import models, schemas
from .database import db

# Get collections
bus_collection = db.get_collection("buses")
route_collection = db.get_collection("routes")
stop_collection = db.get_collection("stops")
feedback_collection = db.get_collection("feedback")
hardware_location_collection = db.get_collection("hardware_locations")
blocked_mac_collection = db.get_collection("blocked_macs")


async def get_bus(bus_id: str):
    return await bus_collection.find_one({"_id": ObjectId(bus_id)})

async def get_bus_by_mac(mac_address: str):
    return await bus_collection.find_one({"mac_address": mac_address})

async def get_buses(skip: int = 0, limit: int = 100):
    buses = await bus_collection.find().skip(skip).limit(limit).to_list(limit)
    print(f"DEBUG: get_buses returning {len(buses)} buses")
    return buses

async def create_bus(bus: models.Bus):
    bus_dict = bus.model_dump(by_alias=True, exclude=["id"])
    result = await bus_collection.insert_one(bus_dict)
    new_bus = await bus_collection.find_one({"_id": result.inserted_id})
    return new_bus

async def update_bus_location(mac_address: str, lat: float | None, lon: float | None, seats_available: int, pm2_5: float, pm10: float, bus_name: str = None, temp: float = 0.0, hum: float = 0.0, rssi: int = None):
    # This is an 'upsert' operation: it updates a bus if it exists, or creates it if it doesn't.
    # This is useful for when a bus device comes online for the first time.
    update_data = {
        "seats_available": seats_available,
        "pm2_5": pm2_5,
        "pm10": pm10,
        "temp": temp,
        "hum": hum
    }
    
    # Only update location if valid coordinates are provided
    if lat is not None:
        update_data["current_lat"] = lat
    if lon is not None:
        update_data["current_lon"] = lon
    if rssi is not None:
        update_data["rssi"] = rssi
        
    if bus_name:
        # Prevent overwriting a good name with a default "Bus-MAC" name
        # Only update if the new name is NOT a generated default, OR if we are creating a new bus
        # This logic is tricky in an upsert, so we rely on the caller or check existence first?
        # Simpler approach: If the caller passed a name, trust it? 
        # No, mqtt.py generates a default. We should filter it there or here.
        # Let's filter here: access DB to check existing name if new one is generic.
        
        # Actually, let's keep it simple: Update name if provided. 
        # But we will rely on mqtt.py to NOT pass a default name if it's not in the payload.
        update_data["bus_name"] = bus_name
        
    result = await bus_collection.update_one(
        {"mac_address": mac_address},
        {"$set": update_data},
        upsert=True
    )
    print(f"DEBUG: update_bus_location result matched={result.matched_count}, upserted={result.upserted_id}, modified={result.modified_count}")
    if result.matched_count == 1 or result.upserted_id:
        return await get_bus_by_mac(mac_address)
    return None

async def delete_bus(mac_address: str):
    result = await bus_collection.delete_one({"mac_address": mac_address})
    return result.deleted_count > 0

async def get_route(route_id: str):
    return await route_collection.find_one({"_id": ObjectId(route_id)})

async def get_routes(skip: int = 0, limit: int = 100):
    return await route_collection.find().skip(skip).limit(limit).to_list(limit)

async def create_route(route: models.Route):
    route_dict = route.model_dump(by_alias=True, exclude=["id"])
    result = await route_collection.insert_one(route_dict)
    new_route = await route_collection.find_one({"_id": result.inserted_id})
    return new_route

async def get_stop(stop_id: str):
    return await stop_collection.find_one({"_id": ObjectId(stop_id)})

async def get_stops(skip: int = 0, limit: int = 100):
    return await stop_collection.find().skip(skip).limit(limit).to_list(limit)

async def create_stop(stop: models.Stop):
    stop_dict = stop.model_dump(by_alias=True, exclude=["id"])
    result = await stop_collection.insert_one(stop_dict)
    new_stop = await stop_collection.find_one({"_id": result.inserted_id})
    return new_stop

async def get_stops_for_route(route_id: str):
    route = await get_route(route_id)
    if route and "stops" in route:
        stop_ids = route["stops"]
        return await stop_collection.find({"_id": {"$in": stop_ids}}).to_list(length=None)
    return []

async def create_feedback(feedback: models.Feedback):
    feedback_dict = feedback.model_dump(by_alias=True, exclude=["id"])
    result = await feedback_collection.insert_one(feedback_dict)
    new_feedback = await feedback_collection.find_one({"_id": result.inserted_id})
    return new_feedback

async def get_feedback(skip: int = 0, limit: int = 100):
    return await feedback_collection.find().sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

async def create_hardware_location(location: models.HardwareLocation):
    location_dict = location.model_dump(by_alias=True, exclude=["id"])
    result = await hardware_location_collection.insert_one(location_dict)
    new_location = await hardware_location_collection.find_one({"_id": result.inserted_id})
    return new_location

async def get_hardware_locations(skip: int = 0, limit: int = 100):
    return await hardware_location_collection.find().sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

# --- MAC Address Blocking ---
async def block_mac_address(mac: models.BlockedMAC):
    mac_dict = mac.model_dump(by_alias=True, exclude=["id"])
    await blocked_mac_collection.update_one(
        {"mac_address": mac.mac_address},
        {"$set": mac_dict},
        upsert=True
    )
    return await blocked_mac_collection.find_one({"mac_address": mac.mac_address})

async def is_mac_blocked(mac_address: str) -> bool:
    return await blocked_mac_collection.find_one({"mac_address": mac_address}) is not None

# --- PM Zones ---
pm_zone_collection = db.get_collection("pm_zones")

async def create_pm_zone(zone: models.PMZone):
    zone_dict = zone.model_dump(by_alias=True, exclude=["id"])
    result = await pm_zone_collection.insert_one(zone_dict)
    new_zone = await pm_zone_collection.find_one({"_id": result.inserted_id})
    return new_zone

async def get_pm_zones(skip: int = 0, limit: int = 100):
    return await pm_zone_collection.find().skip(skip).limit(limit).to_list(limit)

async def delete_pm_zone(zone_id: str):
    result = await pm_zone_collection.delete_one({"_id": ObjectId(zone_id)})
    return result.deleted_count > 0

async def update_pm_zone_stats(zone_id: ObjectId, avg_pm25: float, avg_pm10: float):
    from datetime import datetime
    await pm_zone_collection.update_one(
        {"_id": zone_id},
        {
            "$set": {
                "avg_pm25": avg_pm25, 
                "avg_pm10": avg_pm10,
                "last_updated": datetime.utcnow()
            }
        }
    )
