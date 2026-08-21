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

from app.config import settings

def start_ngrok_tunnel() -> str:
    raw_target = (settings.NGROK_DOMAIN or os.getenv("NGROK_DOMAIN", "") or settings.NGROK_URL or os.getenv("NGROK_URL", "")).strip()
    ngrok_token = (settings.NGROK_AUTHTOKEN or os.getenv("NGROK_AUTHTOKEN", "")).strip()
    public_url = ""

    clean_domain = raw_target.replace("https://", "").replace("http://", "").strip("/")
    
    if raw_target or ngrok_token or os.getenv("ENABLE_NGROK", "").lower() in ("true", "1"):
        try:
            import platform
            from pathlib import Path
            from pyngrok import ngrok, conf

            # Configure persistent binary path across runs so it NEVER re-downloads each time
            if platform.system() == "Windows":
                persist_dir = Path(os.environ.get("APPDATA", Path.home())) / "yt-booster-node" / "ngrok"
                ngrok_bin = persist_dir / "ngrok.exe"
            else:
                persist_dir = Path.home() / ".config" / "yt-booster-node" / "ngrok"
                ngrok_bin = persist_dir / "ngrok"

            persist_dir.mkdir(parents=True, exist_ok=True)
            pyngrok_config = conf.PyngrokConfig(ngrok_path=str(ngrok_bin))

            if ngrok_token:
                ngrok.set_auth_token(ngrok_token, pyngrok_config=pyngrok_config)

            # Kill any existing ngrok process for this config to avoid ERR_NGROK_108 agent limits
            try:
                ngrok.kill(pyngrok_config=pyngrok_config)
            except Exception:
                pass

            connect_kwargs = {"pyngrok_config": pyngrok_config}
            if clean_domain:
                connect_kwargs["domain"] = clean_domain

            tunnel = ngrok.connect(settings.PORT, **connect_kwargs)
            public_url = tunnel.public_url
            print("\n" + "=" * 65)
            print(f"  🚀 NGROK PUBLIC TUNNEL ACTIVE: {public_url}")
            print(f"  🔗 Connect Hostinger Laravel Device API to: {public_url}")
            print("=" * 65 + "\n")
        except Exception as e:
            err_str = str(e)
            print(f"\n⚠️ Could not start ngrok tunnel via pyngrok ({clean_domain}): {err_str}")
            if "ERR_NGROK_105" in err_str or "authtoken" in err_str.lower():
                print("💡 TIP: The NGROK_AUTHTOKEN in your .env file is invalid.")
                print("👉 Please copy your actual authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken\n")
            elif "ERR_NGROK_334" in err_str:
                print("💡 TIP: This endpoint is already online elsewhere.")
                print("👉 Please close any active terminal window running ngrok CLI, or stop your existing endpoint on dashboard.ngrok.com.\n")

    # Fallback to local ngrok API inspection if empty
    if not public_url:
        try:
            from app.services.device_registrar import detect_active_ngrok_url
            public_url = detect_active_ngrok_url()
        except Exception:
            pass

    return public_url

if __name__ == "__main__":
    public_url = start_ngrok_tunnel()
    
    # Auto-register device with Laravel web server
    try:
        from app.services.device_registrar import register_device_with_laravel
        register_device_with_laravel(public_url=public_url)
    except Exception as e:
        print(f"⚠️ Device auto-registration skipped: {e}")

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


