# SUT Smart Bus - Backend Server (Windows Server 2016)

FastAPI backend server for the SUT Smart Bus tracking system.  
**This version is designed for Windows Server 2016 without Docker.**

## Prerequisites

1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **MongoDB Community Server** - [Download](https://www.mongodb.com/try/download/community)
3. **Mosquitto MQTT Broker** - [Download](https://mosquitto.org/download/)

## Quick Start

### 1. Install Dependencies

First, install MongoDB and Mosquitto as Windows Services:
- MongoDB: Run installer, select "Complete" and "Install as Service"
- Mosquitto: Run installer, then configure (see below)

### 2. Configure Mosquitto

Create or edit `C:\Program Files\mosquitto\mosquitto.conf`:
```
listener 1883
listener 9001
protocol websockets
allow_anonymous true
```

Start Mosquitto service:
```cmd
net start mosquitto
```

### 3. Setup Server

```cmd
cd scripts
setup.bat
```

This will:
- Create Python virtual environment
- Install all dependencies
- Create `.env` from template

### 4. Configure Environment

Edit `.env` file:
```env
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MONGODB_URL=mongodb://localhost:27017/sut_smart_bus
TZ=Asia/Bangkok
```

### 5. Start Server

```cmd
scripts\start_server.bat
```

This starts:
- **Main Server** on http://localhost:8000
- **Telemetry Service** for GPS/sensor data

### 6. Stop Server

```cmd
scripts\stop_server.bat
```

## Firewall Configuration

Open these ports in Windows Firewall:
- **8000** - FastAPI server
- **1883** - MQTT broker
- **9001** - MQTT WebSocket
- **27017** - MongoDB (optional, for remote access)

PowerShell commands:
```powershell
netsh advfirewall firewall add rule name="SUT-FastAPI" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="SUT-MQTT" dir=in action=allow protocol=TCP localport=1883
netsh advfirewall firewall add rule name="SUT-MQTT-WS" dir=in action=allow protocol=TCP localport=9001
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/api/buses` | GET | List all buses |
| `/api/ring` | POST | Ring bus bell |
| `/count` | GET | Current passenger count |
| `/dashboard` | GET | Web dashboard |

## Project Structure

```
├── app/
│   ├── main.py         # FastAPI application
│   ├── crud.py         # Database operations
│   ├── models.py       # Pydantic models
│   ├── mqtt.py         # MQTT client
│   └── static/         # Static files
├── telemetry/          # Telemetry service
├── scripts/
│   ├── setup.bat       # First-time setup
│   ├── start_server.bat
│   └── stop_server.bat
├── .env.example        # Environment template
└── requirements.txt    # Python dependencies
```

## Troubleshooting

### MongoDB not starting
```cmd
net start MongoDB
```

### Mosquitto not starting
```cmd
net start mosquitto
```

### Port already in use
```cmd
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

## Related Repositories

- [sut-smart-bus-app](https://github.com/YOUR_USERNAME/sut-smart-bus-app) - Mobile app
- [sut-smart-bus-hardware](https://github.com/YOUR_USERNAME/sut-smart-bus-hardware) - ESP32 firmware

## License

MIT License
