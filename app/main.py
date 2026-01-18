from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, BackgroundTasks, Body, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime, timedelta
import json
import os
import time
import sqlite3
from contextlib import asynccontextmanager

from app import crud, models, schemas
from app.schemas import BusLocation
from core.config import settings
from core.auth import APIKeyMiddleware
from core.auth import APIKeyMiddleware
from app.mqtt import client as mqtt_client, connect_mqtt, start_mqtt_loop, stop_mqtt_loop, set_main_loop, on_message as mqtt_on_message, TOPIC_APP_LOCATION, TOPIC_IR_TRIGGER, TOPIC_BUS_DOOR_COUNT

TOPIC_BUS_STATUS = "sut/bus/+/status"
DB_FILE = "bus_passengers.db"

# Initialize SQLite
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS counts (time TEXT, direction TEXT, total INTEGER)")
        conn.commit()
    print("[OK] SQLite Database Initialized")

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
    
    # Pass the main loop to MQTT module for thread-safe DB operations
    set_main_loop(app.state.loop)
    
    # Create DB indexes (optional - app will work without MongoDB)
    try:
        await crud.bus_collection.create_index("mac_address", unique=True)
        await crud.blocked_mac_collection.create_index("mac_address", unique=True)
        print("[OK] Successfully created database indexes.")
    except Exception as e:
        print(f"[WARN] Could not create database indexes: {e}")
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
            
        # Delegate other topics to the main mqtt module handler
        if msg.topic != TOPIC_BUS_DOOR_COUNT:
            mqtt_on_message(client, userdata, msg)

    # Assign the handler and connect the MQTT client
    mqtt_client.on_message = on_message_handler
    
    print(f"Attempting to connect to MQTT Broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")

    try:
        connect_mqtt()
        mqtt_client.subscribe(TOPIC_BUS_DOOR_COUNT)
        # We don't subscribe to GPS/Status here anymore, the telemetry service handles it.
        start_mqtt_loop()
        print("[OK] MQTT client connected successfully")
    except Exception as e:
        print(f"[WARN] Could not connect to MQTT broker: {e}")

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

# Mount firmware directory for OTA updates
if not os.path.exists(settings.FIRMWARE_DIR):
    os.makedirs(settings.FIRMWARE_DIR)
app.mount("/firmware", StaticFiles(directory=settings.FIRMWARE_DIR), name="firmware")

# API Key Authentication middleware (only active if API_SECRET_KEY is set)
app.add_middleware(APIKeyMiddleware)

# CORS middleware - use origins from config
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log auth status on startup
if settings.API_SECRET_KEY:
    print("[SECURE] API Key Authentication: ENABLED")
else:
    print("[OPEN] API Key Authentication: DISABLED (open access)")

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


# =============================================================================
# Route File Storage Endpoints
# Allows admin/debug users to upload routes that sync to all clients
# =============================================================================

ROUTES_DIR = "routes"
os.makedirs(ROUTES_DIR, exist_ok=True)

class RouteData(BaseModel):
    routeId: str
    routeName: str
    waypoints: list
    busId: Optional[str] = None
    routeColor: Optional[str] = "#2563eb"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


@app.get("/api/routes/list")
async def list_route_files():
    """
    List all available route files.
    Returns basic info (id, name, color) without full waypoint data.
    """
    routes = []
    try:
        for filename in os.listdir(ROUTES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(ROUTES_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        route_data = json.load(f)
                        routes.append({
                            "routeId": route_data.get("routeId", filename.replace('.json', '')),
                            "routeName": route_data.get("routeName", "Unnamed Route"),
                            "routeColor": route_data.get("routeColor", "#2563eb"),
                            "waypointCount": len(route_data.get("waypoints", [])),
                            "stopCount": sum(1 for wp in route_data.get("waypoints", []) if wp.get("isStop")),
                            "updatedAt": route_data.get("updatedAt"),
                        })
                except Exception as e:
                    print(f"Error reading route file {filename}: {e}")
    except Exception as e:
        print(f"Error listing routes: {e}")
    
    return {"routes": routes, "count": len(routes)}


@app.get("/api/routes/{route_id}")
async def get_route_file(route_id: str):
    """
    Get full route data by route ID.
    Returns complete route including all waypoints.
    """
    # Security: Prevent path traversal
    if ".." in route_id or "/" in route_id or "\\" in route_id:
        raise HTTPException(status_code=400, detail="Invalid route ID")
    
    filepath = os.path.join(ROUTES_DIR, f"{route_id}.json")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Route not found")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading route: {str(e)}")


@app.post("/api/routes")
async def save_route_file(route: RouteData):
    """
    Save or update a route.
    Used by admin/debug mode in the app to sync routes to server.
    """
    route_dict = route.model_dump()
    
    # Set timestamps
    now = time.strftime('%Y-%m-%dT%H:%M:%S+07:00')
    if not route_dict.get("createdAt"):
        route_dict["createdAt"] = now
    route_dict["updatedAt"] = now
    
    # Security: Validate route ID format
    route_id = route_dict.get("routeId", "")
    if not route_id or ".." in route_id or "/" in route_id or "\\" in route_id:
        raise HTTPException(status_code=400, detail="Invalid route ID")
    
    filepath = os.path.join(ROUTES_DIR, f"{route_id}.json")
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(route_dict, f, ensure_ascii=False, indent=2)
        
        print(f"📍 Route saved: {route_dict.get('routeName')} ({route_id})")
        return {
            "success": True,
            "routeId": route_id,
            "message": f"Route '{route_dict.get('routeName')}' saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving route: {str(e)}")


@app.delete("/api/routes/{route_id}")
async def delete_route_file(route_id: str):
    """
    Delete a route by ID.
    """
    # Security: Prevent path traversal
    if ".." in route_id or "/" in route_id or "\\" in route_id:
        raise HTTPException(status_code=400, detail="Invalid route ID")
    
    filepath = os.path.join(ROUTES_DIR, f"{route_id}.json")
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Route not found")
    
    try:
        os.remove(filepath)
        print(f"🗑️ Route deleted: {route_id}")
        return {"success": True, "message": f"Route {route_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting route: {str(e)}")


# =============================================================================
# OTA (Over-The-Air) Update Endpoints
# =============================================================================

# Ensure firmware directory exists
os.makedirs(settings.FIRMWARE_DIR, exist_ok=True)

# OTA Topics
TOPIC_OTA_ESP32_CAM = "sut/ota/esp32_cam"
TOPIC_OTA_PM = "sut/ota/pm"

class FirmwareUploadResponse(BaseModel):
    success: bool
    filename: str
    device_type: str
    version: str
    size_bytes: int
    download_url: str

class OTATriggerRequest(BaseModel):
    device_type: str  # "esp32_cam" or "pm"
    version: str      # e.g., "1.0.1"
    force: bool = False  # Force update even if same version

class OTATriggerResponse(BaseModel):
    success: bool
    message: str
    topic: str
    payload: dict


@app.post("/api/firmware/upload", response_model=FirmwareUploadResponse)
async def upload_firmware(
    file: UploadFile = File(...),
    device_type: str = Body(..., embed=True),
    version: str = Body(..., embed=True)
):
    """
    Upload a new firmware binary for OTA updates.
    
    - **file**: The .bin firmware file exported from Arduino IDE
    - **device_type**: Either "esp32_cam" or "pm"
    - **version**: Semantic version string, e.g., "1.0.1"
    """
    # Validate device type
    valid_devices = ["esp32_cam", "pm"]
    if device_type not in valid_devices:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid device_type. Must be one of: {valid_devices}"
        )
    
    # Validate file extension
    if not file.filename.endswith('.bin'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .bin files are allowed."
        )
    
    # Create filename
    filename = f"{device_type}_{version}.bin"
    filepath = os.path.join(settings.FIRMWARE_DIR, filename)
    
    # Save file with size limit check
    try:
        contents = await file.read()
        
        # Security: Check file size limit
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        file_size = len(contents)
        print(f"📦 Firmware uploaded: {filename} ({file_size} bytes)")
        
        return FirmwareUploadResponse(
            success=True,
            filename=filename,
            device_type=device_type,
            version=version,
            size_bytes=file_size,
            download_url=f"/firmware/{filename}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save firmware: {str(e)}")


@app.get("/firmware/{filename}")
async def download_firmware(filename: str):
    """
    Download a firmware binary for OTA update.
    ESP32 devices will call this endpoint to fetch the new firmware.
    """
    # Security: Prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Additional validation: only allow expected filename pattern
    if not filename.endswith('.bin'):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join(settings.FIRMWARE_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Firmware not found")
    
    return FileResponse(
        filepath,
        media_type="application/octet-stream",
        filename=filename
    )


@app.get("/api/firmware/list")
async def list_firmware():
    """
    List all available firmware files.
    """
    try:
        files = []
        for filename in os.listdir(settings.FIRMWARE_DIR):
            if filename.endswith('.bin'):
                filepath = os.path.join(settings.FIRMWARE_DIR, filename)
                stat = os.stat(filepath)
                
                # Parse device type and version from filename
                parts = filename.replace('.bin', '').split('_')
                device_type = parts[0] if parts else "unknown"
                version = '_'.join(parts[1:]) if len(parts) > 1 else "unknown"
                
                files.append({
                    "filename": filename,
                    "device_type": device_type,
                    "version": version,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "download_url": f"/firmware/{filename}"
                })
        
        return {"firmware_files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list firmware: {str(e)}")


@app.post("/api/ota/trigger", response_model=OTATriggerResponse)
async def trigger_ota(request: OTATriggerRequest):
    """
    Trigger an OTA update on ESP32 devices via MQTT.
    
    - **device_type**: "esp32_cam" or "pm" (or "all" for both)
    - **version**: Version to update to (firmware file must exist)
    - **force**: Force update even if device has same version
    """
    # Validate device type
    valid_devices = ["esp32_cam", "pm", "all"]
    if request.device_type not in valid_devices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device_type. Must be one of: {valid_devices}"
        )
    
    # Get server base URL (for firmware download)
    # Use the MQTT broker host as server address since they're co-located
    server_host = settings.MQTT_BROKER_HOST
    
    # If running locally (localhost/127.0.0.1), find actual LAN IP
    if server_host in ["localhost", "127.0.0.1", "::1"]:
        try:
            import socket
            # Connect to a public DNS server (doesn't send data) to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(("8.8.8.8", 80))
            server_host = s.getsockname()[0]
            s.close()
            print(f"📍 Auto-detected LAN IP for OTA: {server_host}")
        except Exception as e:
            print(f"⚠️ Could not detect LAN IP: {e}")
            server_host = "203.158.3.14"  # Fallback only if detection fails
    
    # Determine topics to publish to
    topics = []
    if request.device_type == "all":
        topics = [TOPIC_OTA_ESP32_CAM, TOPIC_OTA_PM]
    elif request.device_type == "esp32_cam":
        topics = [TOPIC_OTA_ESP32_CAM]
    else:
        topics = [TOPIC_OTA_PM]
    
    # Build firmware URL and payload
    filename = f"{request.device_type}_{request.version}.bin"
    if request.device_type == "all":
        # For "all", we'll send separate messages with correct filenames
        pass
    else:
        # Check firmware exists
        filepath = os.path.join(settings.FIRMWARE_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=404,
                detail=f"Firmware file not found: {filename}. Upload it first via /api/firmware/upload"
            )
    
    # Publish OTA command to each topic
    results = []
    for topic in topics:
        device = topic.split('/')[-1]  # Extract device type from topic
        fw_filename = f"{device}_{request.version}.bin"
        
        payload = {
            "command": "ota_update",
            "version": request.version,
            "url": f"http://{server_host}:8000/firmware/{fw_filename}",
            "force": request.force,
            "timestamp": int(time.time())
        }
        
        try:
            mqtt_client.publish(topic, json.dumps(payload))
            print(f"📡 OTA command sent to {topic}: v{request.version}")
            results.append({"topic": topic, "success": True})
        except Exception as e:
            print(f"❌ OTA publish error for {topic}: {e}")
            results.append({"topic": topic, "success": False, "error": str(e)})
    
    # Return response
    all_success = all(r["success"] for r in results)
    return OTATriggerResponse(
        success=all_success,
        message=f"OTA update v{request.version} triggered for {request.device_type}",
        topic=", ".join(topics),
        payload={
            "version": request.version,
            "force": request.force,
            "results": results
        }
    )


# =============================================================================
# Air Quality Analytics Endpoints
# =============================================================================

from app import analytics

@app.get("/api/analytics/zones")
async def get_analytics_zones(hours: int = 24, grid_size: float = 0.001, bus_mac: Optional[str] = None):
    """
    Get air quality data grouped by geographic zones for heatmap visualization.
    
    - **hours**: Number of hours of historical data (default: 24)
    - **grid_size**: Grid cell size in degrees (default: 0.001 ≈ 111m)
    - **bus_mac**: Optional filter for specific bus
    
    Returns zones with lat/lon and average PM2.5/PM10 values.
    """
    zones = await analytics.get_zone_heatmap_data(hours=hours, grid_size=grid_size, bus_mac=bus_mac)
    return {
        "zones": zones,
        "count": len(zones),
        "hours": hours,
        "grid_size_meters": int(grid_size * 111000),
        "bus_mac": bus_mac
    }


@app.get("/api/analytics/trends")
async def get_analytics_trends(hours: int = 24, interval: int = 60, bus_mac: Optional[str] = None):
    """
    Get air quality time series data for trend visualization.
    
    - **hours**: Number of hours of data (default: 24)
    - **interval**: Aggregation interval in minutes (default: 60)
    - **bus_mac**: Optional filter for specific bus
    
    Returns time-bucketed PM2.5/PM10 averages.
    """
    series = await analytics.get_time_series_data(hours=hours, interval_minutes=interval, bus_mac=bus_mac)
    return {
        "series": series,
        "count": len(series),
        "hours": hours,
        "interval_minutes": interval,
        "bus_mac": bus_mac
    }


@app.get("/api/analytics/stats")
async def get_analytics_stats(hours: int = 24, bus_mac: Optional[str] = None):
    """
    Get overall air quality statistics for dashboard summary.
    
    - **hours**: Number of hours of data to analyze (default: 24)
    - **bus_mac**: Optional filter for specific bus
    """
    return {
        "stats": stats,
        "hours": hours,
        "bus_mac": bus_mac
    }


# =============================================================================
# Heatmap Endpoints
# =============================================================================

@app.get("/api/heatmap")
async def get_heatmap(limit: int = 5000, range: str = "1h", mode: str = "gradient", grid_size: float = 0.001):
    """
    Get heatmap data for visualization.
    Range options: "now" (30m), "1h", "1d", "1w", "1m" (30d)
    Mode: "gradient" (default, weighted points) or "grid" (averaged cells)
    Grid size: degrees (0.001° ≈ 111m)
    """
    try:
        # Calculate start_time based on range
        now = datetime.utcnow()
        start_time = now - timedelta(hours=1) # Default 1h
        
        if range == "now":
            start_time = now - timedelta(minutes=30)
        elif range == "1h":
            start_time = now - timedelta(hours=1)
        elif range == "1d":
            start_time = now - timedelta(days=1)
        elif range == "1w":
            start_time = now - timedelta(weeks=1)
        elif range == "3m":
            start_time = now - timedelta(days=90)
        elif range == "all":
            start_time = None # Fetch all historical data
        
        # Choose data format based on mode
        if mode == "grid":
            points = await crud.get_pm_grid_data(limit=limit, start_time=start_time, grid_size_degrees=grid_size)
        else:
            points = await crud.get_heatmap_data(limit=limit, start_time=start_time)
            
        return points
    except Exception as e:
        print(f"Error fetching heatmap: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch heatmap data")

# Internal Debug Endpoint
class DebugLocation(BaseModel):
    lat: float
    lon: float
    pm2_5: float
    bus_mac: str = "FAKE-PM-BUS"
    bus_id: Optional[str] = None # Support bus_id from frontend

@app.post("/api/debug/location")
async def create_debug_location(loc: DebugLocation):
    """Inject fake hardware location for testing"""
    try:
        # Prioritize bus_mac, then bus_id, then default
        target_mac = loc.bus_mac if loc.bus_mac != "FAKE-PM-BUS" else (loc.bus_id if loc.bus_id else "FAKE-PM-BUS")
        
        hw_loc = models.HardwareLocation(
            lat=loc.lat,
            lon=loc.lon,
            pm2_5=loc.pm2_5,
            pm10=loc.pm2_5 * 1.5,
            timestamp=datetime.utcnow(),
            bus_mac=target_mac
        )
        await crud.create_hardware_location(hw_loc)
        return {"success": True, "message": f"Debug location injected for {target_mac}"}
    except Exception as e:
        print(f"Error creating debug location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/debug/location/{bus_mac}")
async def delete_debug_location(bus_mac: str):
    """Clear simulation history for a specific bus"""
    try:
        deleted_count = await crud.delete_hardware_locations_by_mac(bus_mac)
        return {"status": "success", "deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
