# YT Booster - Desktop Automation Node

YT Booster is a high-performance, cross-platform desktop automation client for YouTube campaigns. It pairs a **Tauri v2 + Vanilla JS** user interface with an embedded **Python / Chrome Automation Engine** running as a native sidecar.

---

## ✨ Features

- **Embedded Engine**: Python automation backend is bundled as a native binary (`yt-node`) — no Python or dependency setup required for end users.
- **Chrome Profile Management**: Supports fingerprint randomization, proxy rotation, and CDP cookie injection.
- **System Tray Integration**: Runs quietly in the background and minimizes to the system tray.
- **Live Logs & Real-Time Telemetry**: Real-time CPU, RAM, active campaign tracking, and log streaming.
- **Cross-Platform Installers**: Builds standard `.msi` / `.exe` (Windows) and `.dmg` (macOS) installers.

---

## 🏗️ Project Architecture

```
ytd-booster/
├── .github/workflows/
│   └── release.yml        # Multi-platform CI/CD builder & GitHub Releases
├── desktop/               # Tauri v2 Desktop GUI
│   ├── src/               # Glassmorphic Dark Dashboard (HTML/CSS/JS)
│   ├── src-tauri/         # Rust backend, IPC handlers, system tray, sidecar manager
│   ├── build_macos.sh     # Local macOS DMG build script
│   └── build_windows.bat  # Local Windows MSI build script
└── python/                # Automation Engine & FastAPI backend
    ├── app/               # Browser services, CDP actions, polling workers
    ├── run.py             # Engine entry point
    └── yt-node.spec       # PyInstaller standalone binary configuration
```

---

## 🚀 Releasing New Versions (Automated CI/CD)

To automatically compile and publish new Windows `.msi` and macOS `.dmg` installers:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will automatically build the standalone binaries on Windows and macOS runners, package them with Tauri, and create a public GitHub Release.
