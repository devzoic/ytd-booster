"""
Command Dispatcher — Polls Laravel for queued commands and executes them locally.
Replaces ngrok: device pulls commands instead of server pushing to device.
"""

import asyncio
import httpx
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("command_dispatcher")

# Map command names to local API endpoints
COMMAND_MAP = {
    # Profiles
    "create_profiles":       {"method": "POST",   "path": "/api/profiles/create"},
    "launch_browser":        {"method": "POST",   "path": "/api/profiles/launch"},
    "launch_browsers_bulk":  {"method": "POST",   "path": "/api/profiles/launch-bulk"},
    "close_browser":         {"method": "POST",   "path": "/api/profiles/close"},
    "close_browsers_bulk":   {"method": "POST",   "path": "/api/profiles/close-bulk"},
    "get_running_browsers":  {"method": "GET",    "path": "/api/profiles/running"},
    "delete_profile":        {"method": "DELETE", "path": "/api/profiles/{profile_path}"},
    "delete_profiles_bulk":  {"method": "DELETE", "path": "/api/profiles/bulk"},
    "test_proxy":            {"method": "POST",   "path": "/api/profiles/test-proxy"},
    "test_proxies_bulk":     {"method": "POST",   "path": "/api/profiles/test-proxies-bulk"},

    # Campaigns
    "campaign_watch":        {"method": "POST",   "path": "/api/profiles/campaign/watch"},
    "campaign_run_batched":  {"method": "POST",   "path": "/api/profiles/campaign/run-batched"},
    "cancel_campaign":       {"method": "POST",   "path": "/api/profiles/campaign/{campaign_id}/cancel"},
    "sync_campaign_status":  {"method": "POST",   "path": "/api/profiles/campaign/{campaign_id}/sync-status"},

    # Cookies
    "import_cookies":        {"method": "POST",   "path": "/api/profiles/cookies/import"},
    "import_cookies_bulk":   {"method": "POST",   "path": "/api/profiles/cookies/import-bulk"},

    # Video
    "get_video_metadata":    {"method": "POST",   "path": "/api/profiles/video/metadata"},
}


class CommandDispatcher:
    """Polls Laravel for pending commands and executes them on the local Python API."""

    def __init__(self):
        self.running = False
        self.local_base = f"http://127.0.0.1:{settings.PORT}"

    async def start(self):
        """Start the command polling loop."""
        if self.running:
            return

        self.running = True
        logger.info("Command dispatcher started — polling for commands every 5s")

        while self.running:
            try:
                await self._poll_commands()
            except Exception as e:
                logger.error(f"Error in command poll loop: {e}")

            await asyncio.sleep(5)

    async def stop(self):
        """Stop the command polling loop."""
        self.running = False
        logger.info("Command dispatcher stopping...")

    async def _poll_commands(self):
        """Fetch pending commands from Laravel and execute them."""
        import socket
        clean_hostname = socket.gethostname().split(".")[0]

        url = f"{settings.LARAVEL_API_URL.rstrip('/')}/device/commands/pending"
        params = {
            "device_key": settings.SAAS_DEVICE_KEY,
            "device_name": clean_hostname,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10)
                if response.status_code != 200:
                    return

                data = response.json()
                commands = data.get("commands", [])

                if commands:
                    logger.info(f"Received {len(commands)} commands from Laravel")

                for cmd in commands:
                    # Execute each command in background (don't block polling)
                    asyncio.create_task(self._execute_command(cmd))

            except httpx.ConnectError:
                pass  # Laravel unreachable, silent retry
            except Exception as e:
                logger.warning(f"Command poll failed: {e}")

    async def _execute_command(self, cmd: dict):
        """Execute a single command by calling the local Python API."""
        cmd_id = cmd["id"]
        command_name = cmd["command"]
        params = cmd.get("params", {})

        logger.info(f"Executing command #{cmd_id}: {command_name}")

        mapping = COMMAND_MAP.get(command_name)
        if not mapping:
            logger.error(f"Unknown command: {command_name}")
            await self._report_result(cmd_id, "failed", {"error": f"Unknown command: {command_name}"})
            return

        method = mapping["method"]
        path = mapping["path"]

        # Substitute path parameters
        if "{profile_path}" in path and "profile_path" in params:
            path = path.replace("{profile_path}", params.pop("profile_path"))
        if "{campaign_id}" in path and "campaign_id" in params:
            path = path.replace("{campaign_id}", str(params.pop("campaign_id")))

        local_url = f"{self.local_base}{path}"

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(local_url, timeout=600)
                elif method == "POST":
                    response = await client.post(local_url, json=params, timeout=3600)
                elif method == "DELETE":
                    response = await client.request("DELETE", local_url, json=params, timeout=60)
                else:
                    response = await client.post(local_url, json=params, timeout=60)

                result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}

                if response.status_code < 400:
                    logger.info(f"Command #{cmd_id} ({command_name}) completed successfully")
                    await self._report_result(cmd_id, "completed", result)
                else:
                    logger.warning(f"Command #{cmd_id} ({command_name}) failed with status {response.status_code}")
                    await self._report_result(cmd_id, "failed", result)

        except Exception as e:
            logger.error(f"Command #{cmd_id} ({command_name}) execution error: {e}")
            await self._report_result(cmd_id, "failed", {"error": str(e)})

    async def _report_result(self, cmd_id: int, status: str, result: dict):
        """Report command execution result back to Laravel."""
        if not settings.LARAVEL_API_URL or not settings.SAAS_DEVICE_KEY:
            return

        url = f"{settings.LARAVEL_API_URL.rstrip('/')}/device/commands/{cmd_id}/complete"
        payload = {
            "device_key": settings.SAAS_DEVICE_KEY,
            "status": status,
            "result": result,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Reported command #{cmd_id} result ({status}) to Laravel")
                else:
                    logger.warning(f"Failed to report command #{cmd_id}: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to report command #{cmd_id} result: {e}")


# Global instance
command_dispatcher = CommandDispatcher()
