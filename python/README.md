# YT Booster - Python Automation Service

FastAPI-based browser automation node for the YT Booster SaaS application. It manages local Google Chrome profiles, configures proxies, logs in to Google Accounts, and automates video watching, liking, and commenting using Selenium and CDP interaction protocols.

---

## 📋 Windows Setup Guide

Follow these step-by-step instructions to install, configure, and launch this service on any Windows laptop/PC.

### 1. Prerequisites

Before starting, ensure the laptop has:
* **Google Chrome** installed (standard installation path: `C:\Program Files\Google\Chrome\Application\chrome.exe`).
* **Python 3.9 or higher** installed. 
  > [!IMPORTANT]
  > When installing Python on Windows, you **MUST** check the box that says **"Add Python to PATH"** at the bottom of the installer window.
* An active **Ngrok Account** (free registration at [ngrok.com](https://ngrok.com)) to route requests from the Laravel web server to this local laptop node.

---

### 2. Create a Python Virtual Environment
Open **Command Prompt (cmd)** or **PowerShell** and navigate to the directory of this project:
```cmd
cd path\to\yt-booster-python
python -m venv venv
```

---

### 3. Activate the Virtual Environment
Activate the environment so packages are isolated and run locally:
* **For Command Prompt (cmd.exe)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
* **For PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(If you get an execution policy error in PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first, then re-run the activation script).*

Once activated, your terminal prompt will display a `(venv)` prefix.

---

### 4. Install Dependencies
Install all required libraries (FastAPI, Selenium, websockets, pyngrok, etc.):
```cmd
pip install -r requirements.txt
```

---

### 5. Configure the Environment Variables
1. Find the `.env.example` file in the root of the folder.
2. Copy it and rename the copy to `.env`.
3. Open `.env` in a text editor (Notepad, VS Code, etc.) and configure the following parameters:

```ini
# Python Profile Manager Environment Settings
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Ngrok Public Tunnel
# Copy your actual token from https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTHTOKEN=YOUR_NGROK_AUTHTOKEN

# Optional: If you have a static Ngrok domain (highly recommended)
NGROK_DOMAIN=https://your-custom-subdomain.ngrok-free.dev

# Laravel Web Server Settings
# Change this to your live Laravel server URL (e.g. https://youtube.devzoic.com)
LARAVEL_API_URL=https://youtube.devzoic.com

# Device Registration Key
# Get this key from the Laravel Admin Dashboard -> Devices -> "Register New Device" key
SAAS_DEVICE_KEY=your_device_registration_key
```

---

### 6. Start the Server!
With the virtual environment activated, launch the FastAPI service node:
```cmd
python run.py
```

---

## 🔍 How it Works (Post-Launch)

When you run `python run.py`:
1. **Ngrok Tunnel Setup**: The script boots a secure `pyngrok` tunnel and generates a public URL (e.g. `https://your-custom-subdomain.ngrok-free.dev`).
2. **Device Auto-Registration**: It automatically reaches out to your Laravel server, registers this Windows laptop as an active device node using the `SAAS_DEVICE_KEY`, and updates its API URL to your public Ngrok address.
3. **Standby Mode**: The server stands by to receive bulk browser creation, launching, and campaign instructions from the Laravel master panel.

---

## 📁 Repository Structure

```
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Configuration settings & env loading
│   ├── api/
│   │   └── routes/
│   │       ├── profiles.py  # Profile endpoints (launch-bulk, create, delete)
│   │       └── health.py    # Health check
│   ├── models/
│   │   └── profile.py       # Profile schema models
│   ├── services/
│   │   ├── browser_service.py     # Chrome browser spawn & kill handlers
│   │   ├── browser_interaction.py # CDP/Selenium cookie & bot verification scripts
│   │   ├── video_watcher.py       # YouTube playback timing logic
│   │   └── campaign_executor.py   # Multi-profile campaign task queues
│   └── utils/
│       └── logger.py        # Logging configuration
├── requirements.txt         # Package dependencies list
├── run.py                   # Main runner script (handles Ngrok & Laravel registration)
└── README.md                # Setup documentation
```
