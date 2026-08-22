#!/usr/bin/env python3
"""
Application entry point.
Run with: python run.py
"""

import os
import sys
import ssl
import uvicorn

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.config import settings

if __name__ == "__main__":
    # Auto-register device with Laravel web server (no ngrok URL needed)
    try:
        from app.services.device_registrar import register_device_with_laravel
        register_device_with_laravel(public_url="")
    except Exception as e:
        print(f"[!] Device auto-registration skipped: {e}")

    # Disable reload in binary/Tauri environment so Tauri can cleanly kill and control single PID
    is_frozen = getattr(sys, 'frozen', False)
    is_tauri = os.getenv("TAURI_ENV", "").lower() in ("1", "true")
    should_reload = settings.DEBUG and not is_frozen and not is_tauri

    from app.main import app as fastapi_app

    if should_reload:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            log_level="info"
        )
    else:
        uvicorn.run(
            fastapi_app,
            host=settings.HOST,
            port=settings.PORT,
            log_level="info"
        )
