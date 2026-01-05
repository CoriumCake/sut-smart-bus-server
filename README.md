# SUT Smart Bus - Backend Server

FastAPI backend server for the SUT Smart Bus tracking system.

**🌐 Public URL:** https://smartbus.catcode.tech

## Deployment Options

### Option 1: Docker (Recommended) 🐳

Best for production servers including Windows Server 2022.

```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Services included:**
| Container | Port | Purpose |
|-----------|------|---------|
| sut-mongodb | 27017 | MongoDB database |
| sut-mosquitto | 1883, 9001 | MQTT broker |
| sut-server | 8000 | FastAPI server |

### Option 2: Manual Installation

1. **Install Prerequisites:**
   - Python 3.10+
   - MongoDB Community Server
   - Mosquitto MQTT Broker

2. **Setup:**
   ```cmd
   cd scripts
   setup.bat
   ```

3. **Configure `.env`:**
   ```env
   MQTT_BROKER_HOST=localhost
   MQTT_BROKER_PORT=1883
   MONGODB_URL=mongodb://localhost:27017/sut_smart_bus
   TZ=Asia/Bangkok
   ```

4. **Start:**
   ```cmd
   scripts\start_server.bat
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/api/buses` | GET | List all buses |
| `/api/routes/list` | GET | List all routes |
| `/api/ring` | POST | Ring bus bell |
| `/api/firmware/upload` | POST | Upload OTA firmware |
| `/api/ota/trigger` | POST | Trigger OTA update |
| `/count` | GET | Current passenger count |
| `/dashboard` | GET | Web dashboard |

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `sut/bus/gps` | Subscribe | GPS + sensor data from PM module |
| `bus/door/count` | Subscribe | Passenger enter/exit from ESP32-CAM |
| `sut/bus/ring` | Publish | Ring bell command |
| `sut/ota/pm` | Publish | OTA update for PM sensor |
| `sut/ota/esp32_cam` | Publish | OTA update for ESP32-CAM |

## Project Structure

```
├── app/
│   ├── main.py         # FastAPI application
│   ├── crud.py         # Database operations
│   ├── models.py       # Pydantic models
│   ├── mqtt.py         # MQTT client
│   └── static/         # Static files
├── core/
│   ├── config.py       # Settings from .env
│   └── auth.py         # API key middleware
├── docker/
│   └── mosquitto.conf  # MQTT config for Docker
├── scripts/
│   ├── setup.bat       # First-time setup
│   ├── start_server.bat
│   └── stop_server.bat
├── firmware/           # OTA firmware files (.bin)
├── routes/             # Route JSON files
├── Dockerfile          # Docker image
├── docker-compose.yml  # Multi-container setup
├── .env.example        # Environment template
└── requirements.txt    # Python dependencies
```

## Firewall Configuration

Open these ports:
- **8000** - FastAPI server
- **1883** - MQTT broker
- **9001** - MQTT WebSocket
- **27017** - MongoDB (optional)

```powershell
netsh advfirewall firewall add rule name="SUT-FastAPI" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="SUT-MQTT" dir=in action=allow protocol=TCP localport=1883
netsh advfirewall firewall add rule name="SUT-MQTT-WS" dir=in action=allow protocol=TCP localport=9001
```

## Related Repositories

- [sut-smart-bus-app](https://github.com/YOUR_USERNAME/sut-smart-bus-app) - Mobile app
- [sut-smart-bus-hardware](https://github.com/YOUR_USERNAME/sut-smart-bus-hardware) - ESP32 firmware

## License

MIT License
