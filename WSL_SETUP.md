# 0 to Hero: Run Server on Ubuntu WSL

This guide assumes you have a **fresh, empty Ubuntu WSL distribution** and **Docker Desktop** installed on Windows.

## Phase 1: Initialize Your Environment

Open your Ubuntu terminal and run these commands one by one.

### 1. Update System Repositories
Refresh the package list to ensure you get the latest software versions.
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Essential Tools
Install `git` (to download code) and `curl` (for health checks).
```bash
sudo apt install -y git curl
```

### 3. Setup Docker
**Option A: Relay to Docker Desktop (Easiest & Recommended)**
You do **NOT** need to `apt install docker` inside Ubuntu. You just need to connect strictly to Docker Desktop.
1. Open **Docker Desktop** on Windows.
2. Go to **Settings > Resources > WSL Integration**.
3. Toggle **ON** "Ubuntu".
4. Click **Apply & Restart**.
5. **Restart Terminal**: Close this Ubuntu window and open it again.
6. Verify: `docker version` should now work.

**Option B: Native Install (Advanced / "Pure" Linux)**
*Only do this if you refuse to use Docker Desktop integration.*

> [!WARNING]
> **If you got a "404 Not Found" or "Release file missing" error:**
> You likely have a broken repository configuration from a failed copy-paste. Run this to clean it up before proceeding:
> ```bash
> sudo rm /etc/apt/sources.list.d/docker.list
> sudo apt update
> ```

**Correct Installation Steps (Ubuntu 24.04 'Noble'):**

```bash
# 1. Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 2. Add the repository (Simpler command for Ubuntu 24.04):
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 3. Install Docker Engine:
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Start Docker Daemon:
sudo service docker start

# 5. Non-root access (Fix Permission Denied):
# Add your user to the docker group so you don't need 'sudo' for every command.
sudo usermod -aG docker $USER
newgrp docker

# 6. Fix "TLS Handshake Timeout" / Network Issues:
# If you get "TLS handshake timeout" or "Temporary failure in name resolution":

# Fix 1: Lower MTU (Common fix for hanging downloads)
sudo ip link set dev eth0 mtu 1350

# Fix 2: Force DNS (If downloads don't start at all)
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null

> [!WARNING]
> The MTU fix (Fix 1) resets after a restart. If it works, you can make it permanent later, but run it now to get your images downloaded.

---

## Phase 5: External Access (LAN/Public IP)

To access your server from other devices (e.g., your phone or public IP), you must allow the ports through Windows Firewall.

### 1. Run PowerShell as Administrator
Open a new **PowerShell** window as **Administrator** (Right-click Start > Terminal (Admin)).

### 2. Add Firewall Rules
Run this command block to open the necessary ports:

```powershell
New-NetFirewallRule -DisplayName "SUT Smart Bus API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "SUT Mosquitto MQTT" -Direction Inbound -LocalPort 1883 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "SUT Mosquitto WS" -Direction Inbound -LocalPort 9001 -Protocol TCP -Action Allow
```

### 3. Verify
You should now be able to access `http://YOUR_PC_IP:8000/health` from other devices.

> 1. **Did you run Step 3?** Run `docker --version`. If it says "command not found", you skipped Step 3. Run the `sudo apt-get install ...` command above again.
> 2. **Is Systemd enabled?**
>    Check if systemd is running: `systemctl list-units --type=service`.
>    If it says "System has not been booted with systemd", enable it:
>    ```bash
>    echo -e "[boot]\nsystemd=true" | sudo tee /etc/wsl.conf
>    ```
>    **Then Restart WSL** (in PowerShell): `wsl --shutdown` and open Ubuntu again.
```

---

## Phase 2: Get the Code

### 1. Create a Project Directory
It is cleaner to keep your projects in your Linux home directory, NOT in `/mnt/c`.
```bash
mkdir -p ~/projects
cd ~/projects
```

### 2. Clone the Repository
Download the server code.
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sut-smart-bus-server.git

# Enter the directory
cd sut-smart-bus-server
```
*(Replace `YOUR_USERNAME` with your actual GitHub username. If you are copying files from Windows, see the "Emergency Copy" section below.)*

---

## Phase 3: Launch the Server

### 1. Start Everything
Use Docker Compose to start MongoDB, Mosquitto, and the API Server.
```bash
docker compose up -d
```

### 2. Watch the Logs (Optional)
Make sure everything is starting up correctly.
```bash
docker compose logs -f
```
*(Press `Ctrl+C` to exit the logs view)*

---

## Phase 4: Usage

### Access from Windows
Open your browser or Postman on Windows and go to:
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Useful Commands
| Action | Command |
| Popping | `docker compose up -d` |
| Stopping | `docker compose down` |
| Restarting | `docker compose restart` |
| Status Check | `docker compose ps` |
| View Logs | `docker compose logs -f` |

---

## 🆘 Troubleshooting & "Emergency Copy"

### "I can't clone because I don't have SSH keys setup!"
If you just want to run the code you already have on Windows (in `c:\tmp\...`):
```bash
# formatted to copy from your current windows path
cp -r /mnt/c/tmp/SutSmartBus/repos-windows/sut-smart-bus-server ~/projects/
cd ~/projects/sut-smart-bus-server
docker compose up -d
```

### "Port is already allocated" error
If you see an error like `Bind for 0.0.0.0:8000 failed: port is already allocated`, it means something else is using that port (maybe a previous python script running in Windows).
- Find and stop the conflicting process, or modify `docker-compose.yml` to use a different port (e.g., `"8001:8000"`).
