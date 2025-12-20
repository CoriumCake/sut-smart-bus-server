import paho.mqtt.client as mqtt
import os
import json
import asyncio
from datetime import datetime
from . import crud, models # Import crud and models from the current package

# Get MQTT broker host from environment variable, with a fallback for local development
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_KEEP_ALIVE = 60

# Define topics
TOPIC_ESP32_GPS = "sut/bus/gps"
TOPIC_APP_LOCATION = "sut/app/bus/location"
TOPIC_IR_TRIGGER = "sut/bus/ir/triggered"
TOPIC_BUS_DOOR_COUNT = "bus/door/count"

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the topic the ESP32 will publish to
        client.subscribe(TOPIC_ESP32_GPS)
        client.subscribe(TOPIC_IR_TRIGGER)
    else:
        print(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    """Callback for when a message is received from a subscribed topic."""
    print(f"Received message from topic {msg.topic}: {msg.payload.decode()}")
    
    # Process the incoming GPS data
    try:
        payload = json.loads(msg.payload.decode())
        
        bus_mac = payload.get("bus_mac")
        if not bus_mac:
            print("Error: bus_mac not found in payload.")
            return

        bus_name = payload.get("bus_name", f"Bus-{bus_mac[-5:]}") # Default name
        lat = payload.get("lat")
        lon = payload.get("lon")
        pm2_5 = payload.get("pm2_5", 0.0)
        pm10 = payload.get("pm10", 0.0)
        seats_available = payload.get("seats_available", 0)

        # Ensure lat and lon are not None before processing location data
        if lat is None or lon is None:
            print(f"Warning: Lat/Lon missing for MAC {bus_mac}. Skipping location update.")
            return

        # Use an event loop for async operations
        loop = asyncio.get_event_loop()
        
        # 1. Update current bus location (upsert)
        loop.run_until_complete(
            crud.update_bus_location(
                mac_address=bus_mac,
                bus_name=bus_name,
                lat=lat,
                lon=lon,
                seats_available=seats_available,
                pm2_5=pm2_5,
                pm10=pm10
            )
        )
        print(f"Updated current location for bus {bus_mac}")

        # 2. Store historical hardware location
        hardware_location = models.HardwareLocation(
            lat=lat,
            lon=lon,
            pm2_5=pm2_5,
            pm10=pm10,
            timestamp=datetime.utcnow()
        )
        loop.run_until_complete(crud.create_hardware_location(hardware_location))
        print(f"Stored historical location for bus {bus_mac}")

        # 3. Re-publish to the app's topic for real-time updates
        client.publish(TOPIC_APP_LOCATION, msg.payload, qos=0, retain=False)
        print(f"Re-published message to {TOPIC_APP_LOCATION}")

    except json.JSONDecodeError:
        print(f"Error decoding JSON payload: {msg.payload.decode()}")
    except Exception as e:
        print(f"An unexpected error occurred in on_message: {e}")

# Create and configure the MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message


def connect_mqtt():
    """Connects the client to the MQTT broker."""
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEP_ALIVE)
    except Exception as e:
        print(f"Error connecting to MQTT Broker: {e}")

def start_mqtt_loop():
    """Starts the MQTT client's network loop."""
    client.loop_start()

def stop_mqtt_loop():
    """Stops the MQTT client's network loop."""
    client.loop_stop()
