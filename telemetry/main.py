import asyncio
import os
import json
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import paho.mqtt.client as mqtt

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TelemetryService")

# Configuration
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/sut_smart_bus")

# Topics
TOPIC_ESP32_GPS = "sut/bus/gps"
TOPIC_BUS_STATUS = "sut/bus/+/status"

# Database Init
client = AsyncIOMotorClient(MONGODB_URL)
db = client.get_database()
bus_collection = db.get_collection("buses")
hardware_location_collection = db.get_collection("hardware_locations")

# Async DB Operations
async def update_bus_location(data):
    try:
        bus_mac = data.get("bus_mac")
        if not bus_mac:
            return

        update_data = {
            "pm2_5": data.get("pm2_5", 0.0),
            "pm10": data.get("pm10", 0.0),
            "temp": data.get("temp", 0.0),
            "hum": data.get("hum", 0.0)
        }
        
        # Only update coords if valid
        lat = data.get("lat")
        lon = data.get("lon")
        if lat is not None and lon is not None:
            update_data["current_lat"] = lat
            update_data["current_lon"] = lon
            
            # Also store history
            await hardware_location_collection.insert_one({
                "lat": lat, "lon": lon, 
                "pm2_5": update_data["pm2_5"],
                "bus_mac": bus_mac,
                "timestamp": datetime.utcnow()
            })

        # Upsert Bus
        await bus_collection.update_one(
            {"mac_address": bus_mac},
            {"$set": update_data},
            upsert=True
        )
        logger.info(f"Updated Bus {bus_mac}: {update_data}")

    except Exception as e:
        logger.error(f"DB Update Error: {e}")

# MQTT Handlers
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        client.subscribe(TOPIC_ESP32_GPS)
        client.subscribe(TOPIC_BUS_STATUS)
    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        # logger.info(f"Received: {msg.topic}") # Debug
        data = json.loads(payload)
        
        # Run async update
        asyncio.run_coroutine_threadsafe(update_bus_location(data), loop)
        
    except Exception as e:
        logger.error(f"Message Error: {e}")

# Startup
if __name__ == "__main__":
    logger.info("Starting Telemetry Service...")
    
    # Event Loop for Motor
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # MQTT Client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        client.loop_start()
        
        # Keep main thread alive
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Stopping...")
        client.loop_stop()
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
