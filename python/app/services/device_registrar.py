import os
import platform
import socket
import subprocess
import sys
import uuid
import psutil
import httpx
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("device_registrar")


def get_real_hardware_specs() -> dict:
    """
    Extract real hardware identification & system specifications from the physical machine.
    Supports macOS, Windows, and Linux.
    """
    system = platform.system()
    hardware_id = ""
    serial_number = ""
    cpu_model = ""
    device_model = ""

    # 1. macOS (Darwin)
    if system == "Darwin":
        try:
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    hardware_id = line.split("=")[1].strip(' <>"')
                elif "IOPlatformSerialNumber" in line:
                    serial_number = line.split("=")[1].strip(' <>"')
                elif '"model"' in line:
                    device_model = line.split("=")[1].strip(' <>"')
        except Exception:
            pass

        try:
            cpu_model = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore").strip()
        except Exception:
            cpu_model = platform.processor() or "Apple Silicon"

    # 2. Windows
    elif system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            hardware_id, _ = winreg.QueryValueEx(key, "MachineGuid")
        except Exception:
            pass

        if not hardware_id:
            try:
                out = subprocess.check_output(
                    "wmic csproduct get uuid",
                    shell=True,
                    stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                lines = [l.strip() for l in out.splitlines() if l.strip() and "UUID" not in l]
                if lines:
                    hardware_id = lines[0]
            except Exception:
                pass

        try:
            out = subprocess.check_output(
                "wmic bios get serialnumber",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            lines = [l.strip() for l in out.splitlines() if l.strip() and "SerialNumber" not in l]
            if lines:
                serial_number = lines[0]
        except Exception:
            pass

        try:
            out = subprocess.check_output(
                "wmic cpu get name",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
            if lines:
                cpu_model = lines[0]
        except Exception:
            cpu_model = platform.processor()

    # 3. Linux
    elif system == "Linux":
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id", "/sys/class/dmi/id/product_uuid"]:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        content = f.read().strip()
                        if content:
                            hardware_id = content
                            break
                except Exception:
                    pass

        if os.path.exists("/sys/class/dmi/id/product_serial"):
            try:
                with open("/sys/class/dmi/id/product_serial", "r") as f:
                    serial_number = f.read().strip()
            except Exception:
                pass

        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            cpu_model = line.split(":")[1].strip()
                            break
            except Exception:
                pass

    # Fallback hardware ID if system calls failed
    if not hardware_id:
        hardware_id = f"mac_{hex(uuid.getnode())[2:]}"

    # Get primary local IP address
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # Hostname & OS description
    raw_hostname = socket.gethostname()
    clean_hostname = raw_hostname.split(".")[0]
    os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"

    # Device type detection (laptop vs desktop)
    has_battery = False
    try:
        has_battery = psutil.sensors_battery() is not None
    except Exception:
        pass
    device_type = "laptop" if (has_battery or "MacBook" in device_model or "MacBook" in raw_hostname) else "desktop"

    total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    cpu_cores = psutil.cpu_count(logical=True) or 1

    return {
        "hardware_id": hardware_id,
        "serial_number": serial_number,
        "hostname": clean_hostname,
        "full_hostname": raw_hostname,
        "device_type": device_type,
        "device_model": device_model,
        "cpu_model": cpu_model or platform.processor() or "Unknown CPU",
        "cpu_cores": cpu_cores,
        "total_ram_gb": total_ram_gb,
        "os_name": os_name,
        "local_ip": local_ip,
        "mac_address": hex(uuid.getnode())[2:],
    }


def get_device_registration_payload(api_url: str = "") -> dict:
    """Build complete JSON registration payload with real system hardware data."""
    hw = get_real_hardware_specs()

    desc_parts = []
    if hw["cpu_model"]:
        desc_parts.append(hw["cpu_model"])
    desc_parts.append(f"{hw['cpu_cores']} Cores")
    desc_parts.append(f"{hw['total_ram_gb']} GB RAM")
    description = " | ".join(desc_parts)

    saas_device_key = settings.SAAS_DEVICE_KEY or os.getenv("SAAS_DEVICE_KEY", "")

    return {
        "device_identifier": hw["hardware_id"],
        "name": hw["hostname"],
        "type": hw["device_type"],
        "os": hw["os_name"],
        "api_url": api_url,
        "device_key": saas_device_key,
        "description": description,
        "meta": {
            "device_identifier": hw["hardware_id"],
            "serial_number": hw["serial_number"],
            "hostname": hw["full_hostname"],
            "device_model": hw["device_model"],
            "cpu_model": hw["cpu_model"],
            "cpu_cores": hw["cpu_cores"],
            "total_ram_gb": hw["total_ram_gb"],
            "local_ip": hw["local_ip"],
            "mac_address": hw["mac_address"],
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }
    }


def detect_active_ngrok_url() -> str:
    """
    Detect active ngrok public URL dynamically:
    1. Query local ngrok inspection API at http://127.0.0.1:4040/api/tunnels (if user ran 'ngrok http 8000')
    2. Check NGROK_DOMAIN / NGROK_URL in settings or env
    """
    # 1. Check local ngrok API (port 4040)
    try:
        with httpx.Client(timeout=2.0) as client:
            res = client.get("http://127.0.0.1:4040/api/tunnels")
            if res.status_code == 200:
                data = res.json()
                for tunnel in data.get("tunnels", []):
                    pub_url = tunnel.get("public_url", "")
                    if pub_url.startswith("https://") or pub_url.startswith("http://"):
                        logger.info(f"Auto-detected active ngrok tunnel from local API: {pub_url}")
                        return pub_url
    except Exception:
        pass

    # 2. Check env variables / settings
    env_domain = settings.NGROK_DOMAIN or os.getenv("NGROK_DOMAIN", "") or os.getenv("NGROK_URL", "")
    if env_domain:
        env_domain = env_domain.strip()
        if not env_domain.startswith("http://") and not env_domain.startswith("https://"):
            env_domain = f"https://{env_domain}"
        return env_domain

    return ""


def register_device_with_laravel(public_url: str = "") -> dict:
    """Send real device hardware registration payload to Laravel server."""
    if not settings.LARAVEL_API_URL:
        logger.warning("LARAVEL_API_URL not configured. Skipping device auto-registration.")
        return {"success": False, "message": "No LARAVEL_API_URL"}

    # Auto-detect ngrok URL if not passed explicitly
    if not public_url:
        public_url = detect_active_ngrok_url()

    device_data = get_device_registration_payload(api_url=public_url)

    # Ensure URL ends with /devices/register
    base_url = settings.LARAVEL_API_URL.rstrip("/")
    if base_url.endswith("/api"):
        endpoint = f"{base_url}/devices/register"
    else:
        endpoint = f"{base_url}/api/devices/register"

    logger.info(f"Auto-registering device '{device_data['name']}' (Hardware ID: {device_data['device_identifier']}) with Laravel at {endpoint}...")

    try:
        with httpx.Client(timeout=10.0) as client:
            headers = {"Content-Type": "application/json"}
            if settings.LARAVEL_API_TOKEN:
                headers["Authorization"] = f"Bearer {settings.LARAVEL_API_TOKEN}"
            if device_data.get("device_key"):
                headers["X-Device-Key"] = device_data["device_key"]

            response = client.post(endpoint, json=device_data, headers=headers)

            if response.status_code in (200, 201):
                res_json = response.json()
                action = res_json.get("action", "processed").upper()
                device_info = res_json.get("device", {})
                device_id = device_info.get("id")

                print("\n" + "=" * 70)
                print(f"  ✅ LARAVEL DEVICE AUTO-REGISTRATION [{action}]")
                print(f"  📌 Device ID    : #{device_id}")
                print(f"  💻 Machine Name : {device_data['name']}")
                print(f"  🆔 Hardware UUID: {device_data['device_identifier']}")
                print(f"  ⚙️ Specs        : {device_data['description']}")
                print(f"  🌐 Ngrok API URL: {public_url or 'Local Only'}")
                print("=" * 70 + "\n")

                logger.info(f"Successfully {action.lower()} device #{device_id} ({device_data['name']}) on Laravel web server.")
                return res_json
            else:
                logger.error(f"Laravel registration failed with HTTP {response.status_code}: {response.text}")
                return {"success": False, "status_code": response.status_code, "body": response.text}
    except Exception as e:
        logger.warning(f"Could not connect to Laravel server to register device: {e}")
        return {"success": False, "error": str(e)}
