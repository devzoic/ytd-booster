# YT Booster - Desktop Automation Node

<div align="center">
  <img src="desktop/src/assets/icon.png" width="96" height="96" alt="YT Booster Logo" style="border-radius: 20px; box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);" />
  <h3>High-Performance Cross-Platform YouTube Automation Client</h3>
  <p>Embedded Python Engine • CDP Stealth Browser Control • Automated Device Registration • Live Telemetry</p>
</div>

---

## 📥 Downloads

Download the latest release for your platform from the [**Releases Page**](https://github.com/devzoic/ytd-booster/releases):

| Operating System | Architecture | Package Format | Download Link |
| :--- | :--- | :--- | :--- |
| **Windows 10 / 11** | 64-bit (`x86_64`) | `.msi` Installer / `.exe` Setup | [Download Windows Release](https://github.com/devzoic/ytd-booster/releases/latest) |
| **macOS (Apple Silicon)** | M1 / M2 / M3 / M4 (`arm64`) | `.dmg` Package | [Download Mac (Apple Silicon)](https://github.com/devzoic/ytd-booster/releases/latest) |
| **macOS (Intel)** | Intel Core (`x86_64`) | `.dmg` Package | [Download Mac (Intel)](https://github.com/devzoic/ytd-booster/releases/latest) |
| **Linux (Ubuntu/Debian)** | 64-bit (`x86_64`) | `.deb` / `.AppImage` | [Download Linux Release](https://github.com/devzoic/ytd-booster/releases/latest) |

---

## 🖥️ Installation Instructions

### 1. Windows Installation

#### Option A: Graphical Installer (No Commands - Recommended)
1. Download **`YT Booster_1.0.0_x64_en-US.msi`** or **`YT Booster_1.0.0_x64-setup.exe`** from [Releases](https://github.com/devzoic/ytd-booster/releases/latest).
2. Double-click the downloaded file.
3. If Windows SmartScreen appears: click **"More info"** ➔ **"Run anyway"**.
4. Follow the setup wizard and click **Finish**.
5. Launch **YT Booster** from your Desktop or Start Menu.

#### Option B: Command Line (Silent / PowerShell)
Open PowerShell or Command Prompt as Administrator:
```powershell
# Silent unattended installation
msiexec.exe /i "YT Booster_1.0.0_x64_en-US.msi" /qn /norestart

# Launch application
Start-Process "C:\Program Files\YT Booster\YT Booster.exe"
```

---

### 2. macOS Installation

#### Option A: Graphical Installer (No Commands - Recommended)
1. Download **`YT Booster_1.0.0_aarch64.dmg`** (Apple Silicon) or **`YT Booster_1.0.0_x64.dmg`** (Intel).
2. Double-click the `.dmg` file to mount it.
3. Drag the **YT Booster** icon into your **Applications** folder.
4. Eject the DMG.
5. Open **YT Booster** from Applications or Spotlight (`Cmd + Space` ➔ "YT Booster").
   > **Note for macOS Gatekeeper**: If you see a warning stating the developer cannot be verified, open **System Settings** ➔ **Privacy & Security** ➔ scroll down and click **"Open Anyway"** (or right-click `YT Booster.app` and choose **Open**).

#### Option B: Terminal Commands
```bash
# 1. Mount the DMG
hdiutil attach "YT Booster_1.0.0_aarch64.dmg"

# 2. Copy to Applications
cp -R "/Volumes/YT Booster/YT Booster.app" /Applications/

# 3. Unmount DMG
hdiutil detach "/Volumes/YT Booster"

# 4. Remove macOS quarantine flag
xattr -cr "/Applications/YT Booster.app"

# 5. Launch the application
open "/Applications/YT Booster.app"
```

---

### 3. Linux (Ubuntu / Debian / Arch / Fedora)

#### Option A: Graphical Installer (No Commands)
* **Debian/Ubuntu (`.deb`)**: Double-click `yt-booster_1.0.0_amd64.deb` and click **Install**.
* **AppImage (`.AppImage`)**: Right-click `yt-booster.AppImage` ➔ **Properties** ➔ **Permissions** ➔ Check **"Allow executing file as program"**, then double-click to launch.

#### Option B: Terminal Commands
```bash
# Debian / Ubuntu (.deb)
sudo dpkg -i yt-booster_1.0.0_amd64.deb
sudo apt-get install -f

# AppImage
chmod +x yt-booster_1.0.0_amd64.AppImage
./yt-booster_1.0.0_amd64.AppImage
```

---

## ⚙️ Initial Configuration (Connecting to Laravel)

1. Open **YT Booster**.
2. Click **Settings (⚙️)** on the left sidebar:
   - **`LARAVEL_API_URL`**: Enter your Laravel web application API URL (e.g. `https://your-domain.com/api`).
   - **`SAAS_DEVICE_KEY`**: Enter the unique Device / Worker Key assigned to this node.
   - **`PORT`**: Default is `8008` (change only if conflicting with existing local ports).
   - **`NGROK_AUTHTOKEN`** *(Optional)*: Enter your ngrok authtoken if using ngrok tunnels.
3. Click **"Save & Apply Settings"**.
4. Click **"Test Connection"** to verify server communication.
5. Return to **Dashboard** and ensure the engine status shows **"Running"**.

---

## 🛠️ Building From Source (For Developers)

### Prerequisites:
- **Node.js**: v18+ (`npm install`)
- **Rust**: Latest stable (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- **Python**: 3.10 or 3.11 (`pip install -r python/requirements.txt`)

### Build Steps:

```bash
# 1. Clone repository
git clone https://github.com/devzoic/ytd-booster.git
cd ytd-booster

# 2. Compile Python Engine Binary (yt-node)
cd python
pip install -r requirements.txt pyinstaller
pyinstaller yt-node.spec --noconfirm
cd ..

# 3. Copy Binary to Tauri Sidecar Folder
mkdir -p desktop/src-tauri/binaries
# On macOS:
cp python/dist/yt-node desktop/src-tauri/binaries/yt-node-$(rustc -Vv | grep host | cut -f2 -d' ')
cp python/dist/yt-node desktop/src-tauri/binaries/yt-node
# On Windows:
# copy python\dist\yt-node.exe desktop\src-tauri\binaries\yt-node-x86_64-pc-windows-msvc.exe
# copy python\dist\yt-node.exe desktop\src-tauri\binaries\yt-node.exe

# 4. Run Locally in Development Mode
cd desktop
npm install
npm run dev

# 5. Compile Release Installer (DMG / MSI)
npm run build
```

---

## 🚀 Releasing Updates via GitHub Actions (CI/CD)

Whenever you push a version tag, GitHub Actions automatically compiles the Python sidecar on Windows and macOS, packages the Tauri installers, and publishes them as a GitHub Release:

```bash
git add .
git commit -m "Update feature XYZ"
git push origin main

# Publish new release
git tag v1.0.1
git push origin v1.0.1
```
