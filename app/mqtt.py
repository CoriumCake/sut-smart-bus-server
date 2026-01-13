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
TOPIC_ESP32_GPS_FAST = "sut/bus/gps/fast"  # Fast GPS-only updates
TOPIC_APP_LOCATION = "sut/app/bus/location"
TOPIC_IR_TRIGGER = "sut/bus/ir/triggered"
TOPIC_BUS_DOOR_COUNT = "bus/door/count"

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the topic the ESP32 will publish to
        client.subscribe(TOPIC_ESP32_GPS)
        client.subscribe(TOPIC_ESP32_GPS_FAST)
        client.subscribe(TOPIC_IR_TRIGGER)
        print(f"Subscribed to: {TOPIC_ESP32_GPS}, {TOPIC_ESP32_GPS_FAST}, {TOPIC_IR_TRIGGER}")
    else:
        print(f"Failed to connect, return code {rc}\n")


# Global loop variable
main_loop = None

def set_main_loop(loop):
    global main_loop
    main_loop = loop

def on_message(client, userdata, msg):
    """Callback for when a message is received from a subscribed topic."""
    print(f"Received message from topic {msg.topic}: {msg.payload.decode()}")
    
    # Process the incoming GPS data
    try:
        payload = json.loads(msg.payload.decode())
        
        # === SECURITY: Validate bus_mac ===
        bus_mac = payload.get("bus_mac")
        if not bus_mac:
            print("Error: bus_mac not found in payload.")
            return
        
        # Sanitize bus_mac (should be MAC address format)
        if not isinstance(bus_mac, str) or len(bus_mac) > 20:
            print(f"Error: Invalid bus_mac format: {bus_mac}")
            return

        # Check if bus_name is in payload, otherwise look up from database
        bus_name = payload.get("bus_name")
        
        if bus_name:
            # Validate/Sanitize
            if isinstance(bus_name, str):
                 bus_name = bus_name[:30]
            else:
                 bus_name = None
        else:
            # If missing, pass None so CRUD doesn't overwrite existing name
            bus_name = None
        
        lat = payload.get("lat")
        lon = payload.get("lon")
        pm2_5 = payload.get("pm2_5", 0.0)
        pm10 = payload.get("pm10", 0.0)
        temp = payload.get("temp", 0.0)
        hum = payload.get("hum", 0.0)
        seats_available = payload.get("seats_available", 0)

        # === SECURITY: Validate numeric types ===
        try:
            if lat is not None:
                lat = float(lat)
                if not (-90 <= lat <= 90):
                    print(f"Error: Invalid latitude: {lat}")
                    return
            if lon is not None:
                lon = float(lon)
                if not (-180 <= lon <= 180):
                    print(f"Error: Invalid longitude: {lon}")
                    return
            pm2_5 = float(pm2_5) if pm2_5 is not None else 0.0
            pm10 = float(pm10) if pm10 is not None else 0.0
            temp = float(temp) if temp is not None else 0.0
            hum = float(hum) if hum is not None else 0.0
            seats_available = int(seats_available) if seats_available is not None else 0
            
            # Sanity checks for sensor data
            pm2_5 = max(0, min(pm2_5, 1000))  # Reasonable PM2.5 range
            pm10 = max(0, min(pm10, 1000))    # Reasonable PM10 range
            seats_available = max(0, min(seats_available, 100))  # Reasonable seat count
        except (ValueError, TypeError) as e:
            print(f"Error: Invalid numeric value in payload: {e}")
            return

        # Ensure lat and lon are not None before processing location data
        # Use thread-safe execution on the main loop
        if main_loop:
            # Handle missing GPS by fetching last known location
            if lat is None or lon is None:
                print(f"Notice: Lat/Lon missing for {bus_mac}. Fetching last known location.")
                # We need to do this via thread-safe call, but run_until_complete is not good here 
                # inside a callback if the loop is running. 
                # We'll just define a background task to handle the whole update logic.
                
                async def process_update_async():
                    nonlocal lat, lon
                    # Fetch last known location
                    existing_bus = await crud.get_bus_by_mac(bus_mac)
                    if existing_bus:
                         if lat is None: lat = existing_bus.get("current_lat")
                         if lon is None: lon = existing_bus.get("current_lon")
                    
                    if lat is None or lon is None: 
                        print(f"Warning: No historical location for {bus_mac}. Cannot save hardware location.")
                        # Still update bus status (for temp/hum/pm display) without location
                        await crud.update_bus_location(
                            mac_address=bus_mac,
                            bus_name=bus_name,
                            lat=0.0, # Placeholder
                            lon=0.0, # Placeholder
                            seats_available=seats_available,
                            pm2_5=pm2_5,
                            pm10=pm10,
                            temp=temp,
                            hum=hum
                        )
                        return

                    # 1. Update current bus location
                    await crud.update_bus_location(
                        mac_address=bus_mac,
                        bus_name=bus_name,
                        lat=lat,
                        lon=lon,
                        seats_available=seats_available,
                        pm2_5=pm2_5,
                        pm10=pm10,
                        temp=temp,
                        hum=hum
                    )

                    # 2. Store historical hardware location
                    hardware_location = models.HardwareLocation(
                        lat=lat,
                        lon=lon,
                        pm2_5=pm2_5,
                        pm10=pm10,
                        timestamp=datetime.utcnow()
                    )
                    await crud.create_hardware_location(hardware_location)
                    print(f"Processed message for {bus_mac} (topic: {msg.topic}). Location: {lat}, {lon}, Temp: {temp}, Hum: {hum}")

                asyncio.run_coroutine_threadsafe(process_update_async(), main_loop)

            else:
                 # We have GPS, proceed as normal
                asyncio.run_coroutine_threadsafe(
                    crud.update_bus_location(
                        mac_address=bus_mac,
                        bus_name=bus_name,
                        lat=lat,
                        lon=lon,
                        seats_available=seats_available,
                        pm2_5=pm2_5,
                        pm10=pm10,
                        temp=temp,
                        hum=hum
                    ),
                    main_loop
                )

                hardware_location = models.HardwareLocation(
                    lat=lat,
                    lon=lon,
                    pm2_5=pm2_5,
                    pm10=pm10,
                    timestamp=datetime.utcnow()
                )
                asyncio.run_coroutine_threadsafe(
                    crud.create_hardware_location(hardware_location),
                    main_loop
                )
                print(f"Processed message for {bus_mac} (topic: {msg.topic}). Loc: {lat}, {lon}")
            
            # 3. Publish to app (this is thread-safe on client object)
            # ONLY publish to the main app topic if this was a full update (not fast GPS)
            # This prevents overwriting sensor data with 0s in the app
            if msg.topic != TOPIC_ESP32_GPS_FAST:
                app_payload = {
                    "bus_mac": bus_mac,
                    "bus_name": bus_name,
                    "lat": lat,
                    "lon": lon,
                    "pm2_5": pm2_5,
                    "pm10": pm10,
                    "temp": temp,
                    "hum": hum,
                    "seats_available": seats_available
                }
                client.publish(TOPIC_APP_LOCATION, json.dumps(app_payload), qos=0, retain=False)
            
        else:
            print("Error: Main event loop not set in mqtt.py")

    except json.JSONDecodeError:
        print(f"Error decoding JSON payload: {msg.payload.decode()}")
    except Exception as e:
        print(f"An unexpected error occurred in on_message: {e}")

# Create and configure the MQTT client
# Use a fixed client ID to easily identify in Mosquitto logs
client = mqtt.Client(client_id="sut-server", clean_session=True)
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
