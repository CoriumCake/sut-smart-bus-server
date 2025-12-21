from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, BackgroundTasks, Body, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List
from pydantic import BaseModel
import asyncio
import json
import os
import time
import sqlite3
from contextlib import asynccontextmanager

from app import crud, models, schemas
from app.schemas import BusLocation
from core.config import settings
from core.auth import APIKeyMiddleware
from app.mqtt import client as mqtt_client, connect_mqtt, start_mqtt_loop, stop_mqtt_loop, TOPIC_APP_LOCATION, TOPIC_IR_TRIGGER, TOPIC_BUS_DOOR_COUNT

TOPIC_BUS_STATUS = "sut/bus/+/status"
DB_FILE = "bus_passengers.db"

# Initialize SQLite
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS counts (time TEXT, direction TEXT, total INTEGER)")
        conn.commit()
    print("✅ SQLite Database Initialized")

# Global passenger count
current_passengers = 0
TOTAL_SEATS = 33

# App lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting application services...")
    init_db()
    
    # Initialize state variables
    app.state.loop = asyncio.get_running_loop()
    
    # Create DB indexes (optional - app will work without MongoDB)
    try:
        await crud.bus_collection.create_index("mac_address", unique=True)
        await crud.blocked_mac_collection.create_index("mac_address", unique=True)
        print("✅ Successfully created database indexes.")
    except Exception as e:
        print(f"⚠️  Warning: Could not create database indexes: {e}")
        print("The server will continue without MongoDB functionality")

    # Define the MQTT on_message callback
    def on_message_handler(client, userdata, msg):
        try:
            payload = msg.payload.decode()
            
            # Handle Bus Door Count (New ESP32)
            if msg.topic == TOPIC_BUS_DOOR_COUNT:
                global current_passengers
                try:
                    data = json.loads(payload)
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Store in SQLite
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("INSERT INTO counts VALUES (?, ?, ?)", 
                                     (timestamp, data.get('dir'), data.get('count')))
                        conn.commit()
                    
                    # Update global count
                    current_passengers = data.get('count', current_passengers)
                    print(f"[{timestamp}] {data.get('dir', 'unknown').upper()} - Total: {current_passengers}")
                    
                    # --- SYNC WITH SEATS ---
                    seats_available = max(0, TOTAL_SEATS - current_passengers)
                    bus_mac = "ESP32-CAM-01" # Default/Mock MAC for the single bus
                    
                    # Update MongoDB (for Map Tab)
                    async def update_seats():
                        await crud.update_bus_location(
                            mac_address=bus_mac,
                            lat=None, lon=None, # Don't update location
                            seats_available=seats_available,
                            pm2_5=0, pm10=0 
                        )
                        # Broadcast update to App
                        updated_bus = await crud.get_bus_by_mac(bus_mac)
                        if updated_bus:
                             app_payload = updated_bus.dict()
                             client.publish(TOPIC_APP_LOCATION, json.dumps(app_payload))
                             
                    loop = app.state.loop
                    asyncio.run_coroutine_threadsafe(update_seats(), loop)

                    # --- APP COMPATIBILITY (Testing Screen) ---
                    # Publish dummy payloads to keep Testing Tab alive (showing stats only)
                    detection_payload = {
                        "entering": 0, 
                        "exiting": 0, 
                        "total_unique_persons": current_passengers,
                        "boxes": [],
                        "processing_time_ms": 0
                    }
                    client.publish("sut/person-detection", json.dumps(detection_payload))

                except Exception as e:
                    print(f"Error processing bus count: {e}")
                return

        except Exception as e:
            print(f"Error in MQTT on_message_handler: {e}")

    # Assign the handler and connect the MQTT client
    mqtt_client.on_message = on_message_handler
    
    print(f"Attempting to connect to MQTT Broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")

    try:
        connect_mqtt()
        mqtt_client.subscribe(TOPIC_BUS_DOOR_COUNT)
        # We don't subscribe to GPS/Status here anymore, the telemetry service handles it.
        start_mqtt_loop()
        print("✅ MQTT client connected successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to MQTT broker: {e}")

    yield

    # Shutdown
    print("Shutting down application services...")
    try:
        stop_mqtt_loop()
    except Exception as e:
        print(f"Error stopping MQTT: {e}")
    
    print("Disconnected from services.")


app = FastAPI(lifespan=lifespan)

# Mount static for dashboard or generic assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API Key Authentication middleware (only active if API_SECRET_KEY is set)
app.add_middleware(APIKeyMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log auth status on startup
if settings.API_SECRET_KEY:
    print(f"🔐 API Key Authentication: ENABLED")
else:
    print(f"🔓 API Key Authentication: DISABLED (open access)")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sut-bus-server"}

@app.get("/")
async def root():
    return {"message": "SUT Smart Bus API (Lite)", "status": "running", "auth": "enabled" if settings.API_SECRET_KEY else "disabled"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    # Get recent events from SQLite
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM counts ORDER BY time DESC LIMIT 20")
            recent = cursor.fetchall()
    except Exception as e:
        print(f"DB Error: {e}")
        recent = []

    rows_html = ""
    for row in recent:
        timestamp, direction, total = row
        css_class = 'enter' if direction == 'enter' else 'exit'
        rows_html += f"""
            <tr class="{css_class}">
                <td>{timestamp}</td><td>{direction.upper()}</td><td>{total}</td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Bus Passenger Counter</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: Arial; max-width: 800px; margin: 50px auto; }}
        .count {{ font-size: 4em; color: #2196F3; text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        .enter {{ background: #d4edda; }}
        .exit {{ background: #f8d7da; }}
    </style>
    </head>
    <body>
        <h1>🚌 Campus Bus Passenger Counter</h1>
        <div class="count">{current_passengers}</div>
        <table>
            <tr><th>Time</th><th>Direction</th><th>Total</th></tr>
            {rows_html}
        </table>
    </body>
    </html>
    """
    return html

@app.get("/count")
async def get_count():
    return {"passengers": current_passengers}

# CRUD Endpoints (Proxies to MongoDB for App)
@app.get("/api/buses", response_model=List[models.Bus])
async def list_buses(skip: int = 0, limit: int = 100):
    return await crud.get_buses(skip=skip, limit=limit)
    
@app.get("/api/routes", response_model=List[models.Route])
async def list_routes(skip: int = 0, limit: int = 100):
    return await crud.get_routes(skip=skip, limit=limit)

@app.get("/api/stops", response_model=List[models.Stop])
async def list_stops(skip: int = 0, limit: int = 100):
    return await crud.get_stops(skip=skip, limit=limit)

# Bus CRUD endpoints (for admin management)
@app.post("/api/buses", response_model=models.Bus)
async def create_bus(bus: models.Bus):
    """Create a new bus"""
    return await crud.create_bus(bus)

@app.put("/api/buses/{mac_address}")
async def update_bus(mac_address: str, bus_data: dict = Body(...)):
    """Update an existing bus by MAC address"""
    result = await crud.bus_collection.update_one(
        {"mac_address": mac_address},
        {"$set": bus_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bus not found")
    return await crud.get_bus_by_mac(mac_address)

@app.delete("/api/buses/{mac_address}")
async def delete_bus(mac_address: str):
    """Delete a bus by MAC address"""
    deleted = await crud.delete_bus(mac_address)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bus not found")
    return {"message": "Bus deleted successfully"}


# Ring Bell Endpoint - Publishes to MQTT to trigger ESP32 buzzer
class RingRequest(BaseModel):
    bus_mac: str = "ESP32-CAM-01"

@app.post("/api/ring")
async def ring_bell(request: RingRequest):
    """
    Send ring command to ESP32 to trigger buzzer/LED
    The ESP32 subscribes to 'sut/bus/ring' and 'sut/bus/+/ring' topics
    """
    try:
        # Publish to ring topic (only once)
        mqtt_client.publish("sut/bus/ring", json.dumps({
            "command": "ring",
            "bus_mac": request.bus_mac,
            "timestamp": int(time.time())
        }))
        
        print(f"🔔 Ring command sent to {request.bus_mac}")
        return {"success": True, "message": f"Ring signal sent to {request.bus_mac}"}
    except Exception as e:
        print(f"❌ Ring error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send ring: {str(e)}")


# Bus Route Mapping Endpoint - Serves centralized mapping data
# This allows the app to download the latest bus-route mappings on startup
BUS_ROUTE_MAPPING = {
    "version": 1,
    "lastUpdated": "2025-12-19T09:00:00+07:00",
    "mappings": [
        {
            "bus_mac": "28:56:2F:49:F7:00",
            "bus_name": "SUT-BUS-01",
            "route_id": "route_1765852937753_9hdm9wd76",
            "route_name": "Red routes"
        }
    ],
    "routes": [
        {
            "route_id": "route_1765852937753_9hdm9wd76",
            "route_name": "Red routes",
            "route_color": "#e11d48",
            "file": "red_routes.json"
        }
    ]
}

@app.get("/api/bus-route-mapping")
async def get_bus_route_mapping(version: int = 0):
    """
    Get the centralized bus-route mapping.
    If client passes version param, returns empty if already up-to-date.
    """
    if version >= BUS_ROUTE_MAPPING["version"]:
        return {"upToDate": True, "version": BUS_ROUTE_MAPPING["version"]}
    return BUS_ROUTE_MAPPING
