"""
Dashboard routes for Python monitoring server.
Provides system stats, profile info, and campaign progress with a modern web UI.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import psutil
import asyncio
from typing import Dict, Any, List
from app.utils.logger import setup_logger
from app.models.response import APIResponse

logger = setup_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Setup templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard HTML page."""
    return templates.TemplateResponse(request, "dashboard.html")


@router.get("/api/stats", response_model=APIResponse)
async def get_system_stats():
    """Get system stats (CPU, RAM, etc.)."""
    try:
        # CPU stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory stats
        memory = psutil.virtual_memory()
        
        # Disk stats
        disk = psutil.disk_usage('/')
        
        return APIResponse(
            success=True,
            message="System stats retrieved",
            data={
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else 0,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": disk.percent,
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.get("/api/profiles", response_model=APIResponse)
async def get_profile_stats():
    """Get profile statistics and running Chrome processes."""
    try:
        # Get running Chrome processes
        chrome_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    profile_dir = None
                    for i, arg in enumerate(cmdline or []):
                        if '--user-data-dir=' in arg:
                            profile_dir = arg.split('=')[1]
                            break
                    
                    chrome_processes.append({
                        "pid": proc.info['pid'],
                        "memory_percent": round(proc.info['memory_percent'], 2) if proc.info['memory_percent'] is not None else 0.0,
                        "cpu_percent": round(proc.info['cpu_percent'], 2) if proc.info['cpu_percent'] is not None else 0.0,
                        "profile_dir": profile_dir,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Group by profile
        profile_stats = {}
        for proc in chrome_processes:
            profile_dir = proc.get('profile_dir')
            if profile_dir:
                if profile_dir not in profile_stats:
                    profile_stats[profile_dir] = {
                        "processes": 0,
                        "total_memory": 0,
                        "total_cpu": 0,
                    }
                profile_stats[profile_dir]["processes"] += 1
                profile_stats[profile_dir]["total_memory"] += proc["memory_percent"]
                profile_stats[profile_dir]["total_cpu"] += proc["cpu_percent"]
        
        return APIResponse(
            success=True,
            message=f"Found {len(chrome_processes)} Chrome processes across {len(profile_stats)} profiles",
            data={
                "total_chrome_processes": len(chrome_processes),
                "profiles_running": len(profile_stats),
                "profiles": profile_stats,
                "processes": chrome_processes[:50],  # Limit to avoid huge response
            }
        )
    except Exception as e:
        logger.error(f"Error getting profile stats: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.get("/api/campaigns", response_model=APIResponse)
async def get_campaign_stats():
    """Get campaign execution stats from cache."""
    try:
        from app.services.campaign_cache import CampaignCache
        
        campaigns = CampaignCache.get_all_campaigns()
        
        # Summarize
        total_campaigns = len(campaigns)
        total_profiles = sum(c.get("total_profiles", 0) for c in campaigns.values() if c)
        completed_profiles = sum(c.get("completed_profiles", 0) for c in campaigns.values() if c)
        pending_profiles = sum(c.get("pending_profiles", 0) for c in campaigns.values() if c)
        
        return APIResponse(
            success=True,
            message=f"Found {total_campaigns} campaigns in cache",
            data={
                "total_campaigns": total_campaigns,
                "total_profiles": total_profiles,
                "completed_profiles": completed_profiles,
                "pending_profiles": pending_profiles,
                "campaigns": campaigns,
            }
        )
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.get("/api/logs", response_model=APIResponse)
async def get_recent_logs(limit: int = 100):
    """Get recent log entries from the centralized logger buffer."""
    from app.utils.logger import get_log_buffer
    
    logs = get_log_buffer()
    
    return APIResponse(
        success=True,
        message=f"Retrieved {min(limit, len(logs))} log entries",
        data={
            "logs": logs[-limit:],
            "total": len(logs),
        }
    )


@router.delete("/api/logs", response_model=APIResponse)
async def clear_logs():
    """Clear the log buffer."""
    from app.utils.logger import clear_log_buffer
    
    clear_log_buffer()
    
    return APIResponse(
        success=True,
        message="Logs cleared",
        data=None
    )


@router.post("/api/campaigns/{campaign_id}/stop", response_model=APIResponse)
async def stop_campaign(campaign_id: int):
    """Stop a campaign and notify Laravel server."""
    try:
        from app.services.campaign_cache import CampaignCache
        import httpx
        import os
        
        # Cancel the campaign locally
        CampaignCache.cancel_campaign(campaign_id)
        
        # Notify Laravel server
        laravel_url = os.getenv("LARAVEL_URL", "http://youtube.test")
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(
                    f"{laravel_url}/api/campaigns/{campaign_id}/update-status",
                    json={"status": "cancelled", "device": "python_dashboard"},
                    headers={"Accept": "application/json"}
                )
                laravel_response = response.json() if response.status_code == 200 else {"error": response.text}
            except Exception as e:
                laravel_response = {"error": str(e)}
        
        logger.info(f"Campaign {campaign_id} stopped from dashboard")
        
        return APIResponse(
            success=True,
            message=f"Campaign {campaign_id} stopped",
            data={
                "campaign_id": campaign_id,
                "status": "cancelled",
                "laravel_response": laravel_response
            }
        )
    except Exception as e:
        logger.error(f"Error stopping campaign {campaign_id}: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.post("/api/campaigns/{campaign_id}/pause", response_model=APIResponse)
async def pause_campaign(campaign_id: int):
    """Pause a campaign and notify Laravel server."""
    try:
        from app.services.campaign_cache import CampaignCache
        import httpx
        import os
        
        # Mark as cancelled (paused)
        CampaignCache.cancel_campaign(campaign_id)
        
        # Notify Laravel server
        laravel_url = os.getenv("LARAVEL_URL", "http://youtube.test")
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(
                    f"{laravel_url}/api/campaigns/{campaign_id}/update-status",
                    json={"status": "paused", "device": "python_dashboard"},
                    headers={"Accept": "application/json"}
                )
                laravel_response = response.json() if response.status_code == 200 else {"error": response.text}
            except Exception as e:
                laravel_response = {"error": str(e)}
        
        logger.info(f"Campaign {campaign_id} paused from dashboard")
        
        return APIResponse(
            success=True,
            message=f"Campaign {campaign_id} paused",
            data={
                "campaign_id": campaign_id,
                "status": "paused",
                "laravel_response": laravel_response
            }
        )
    except Exception as e:
        logger.error(f"Error pausing campaign {campaign_id}: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.delete("/api/campaigns/{campaign_id}", response_model=APIResponse)
async def clear_campaign(campaign_id: int):
    """Clear a campaign from the Python cache."""
    try:
        from app.services.campaign_cache import CampaignCache
        
        CampaignCache.clear_campaign(campaign_id)
        
        logger.info(f"Campaign {campaign_id} cleared from cache")
        
        return APIResponse(
            success=True,
            message=f"Campaign {campaign_id} cleared from cache",
            data={"campaign_id": campaign_id}
        )
    except Exception as e:
        logger.error(f"Error clearing campaign {campaign_id}: {e}")
        return APIResponse(success=False, message=str(e), data=None)


@router.post("/api/campaigns/{campaign_id}/restart", response_model=APIResponse)
async def restart_campaign(campaign_id: int):
    """Restart a stopped/cancelled campaign - resets failed profiles to pending."""
    try:
        from app.services.campaign_cache import CampaignCache
        
        result = CampaignCache.restart_campaign(campaign_id)
        
        if result:
            logger.info(f"Campaign {campaign_id} restarted from dashboard")
            return APIResponse(
                success=True,
                message=f"Campaign {campaign_id} restarted - profiles reset to pending",
                data={"campaign_id": campaign_id, "reset_count": result}
            )
        else:
            return APIResponse(
                success=False,
                message=f"Campaign {campaign_id} not found in cache",
                data=None
            )
    except Exception as e:
        logger.error(f"Error restarting campaign {campaign_id}: {e}")
        return APIResponse(success=False, message=str(e), data=None)
