# SUT Smart Bus - Backend Server

FastAPI backend server for the SUT Smart Bus tracking system.

**🌐 Public URL:** https://smartbus.catcode.tech

---

## 🏗️ Architecture

This server runs inside **Docker (WSL)** on Windows Server 2022. It uses **Cloudflare Tunnel** to securely expose the API to the internet without opening firewall ports.

| Component | Technology | Description |
|-----------|------------|-------------|
| **Server** | FastAPI (Python) | Main API logic |
| **Database** | MongoDB | Stores routes, bus data |
| **Broker** | Mosquitto MQTT | Real-time sensor data |
| **Ingress** | Cloudflare Tunnel | Public HTTPS access |
| **Auth** | API Key | Secures API endpoints |

---

## 🚀 Deployment (WSL + Docker)

### 1. Prerequisites
-   **Docker Desktop** (configured for WSL 2)
-   **Cloudflared** (Windows executable)

### 2. Start the Server
Run these commands inside your **WSL Terminal**:
```bash
# Start all services (Server, Mongo, MQTT)
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### 3. Start the Tunnel
Run this command in **Windows PowerShell**:
```powershell
# Start the secure tunnel to https://smartbus.catcode.tech
.\cloudflared.exe tunnel --config .cloudflared\config.yml run
```

> **Note:** Because the app runs in WSL, we use a Windows Port Proxy to forward traffic.
> If the tunnel fails to connect, checks `walkthrough.md` for instructions on updating the WSL IP.

---

## 🔐 Authentication

All API endpoints (except `/health` and `/`) require an API Key.

-   **Header Name:** `X-API-Key`
-   **Key:** `d495128f-9bf7-4f98-8772-65936345aadf` (Set in `docker-compose.yml`)

**Example Request:**
```bash
curl -H "X-API-Key: d495128f-9bf7-4f98-8772-65936345aadf" https://smartbus.catcode.tech/api/buses
```

---

## 📡 API Endpoints

Full documentation is available at: `https://smartbus.catcode.tech/docs`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (No Auth) |
| `/api/buses` | GET | List all active buses |
| `/api/routes` | GET | List bus routes |
| `/api/ring` | POST | Trigger bus buzzer |
| `/api/firmware/upload` | POST | Upload OTA firmware |
| `/api/ota/trigger` | POST | Trigger remote update |
| `/dashboard` | GET | Real-time web dashboard |

---

## 📁 Project Structure

```
├── app/
│   ├── main.py         # Application entry point
│   ├── mqtt.py         # MQTT logic
│   └── ...
├── core/
│   ├── auth.py         # API Key Middleware
│   └── config.py       # Configuration loader
├── .cloudflared/       # Cloudflare Tunnel config
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # Server image definition
└── README.md           # This file
```

## Related Repositories

-   [sut-smart-bus-app](https://github.com/YOUR_USERNAME/sut-smart-bus-app) - Mobile app
-   [sut-smart-bus-hardware](https://github.com/YOUR_USERNAME/sut-smart-bus-hardware) - ESP32 firmware
