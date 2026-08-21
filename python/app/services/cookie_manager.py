"""
Cookie Manager Service - Imports cookies into Chrome profiles using CDP.

Uses Chrome DevTools Protocol to inject cookies at runtime after browser launches.
"""

import json
import time
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CookieManager:
    """Service for managing cookies in Chrome profiles using CDP."""
    
    @classmethod
    async def inject_cookies_via_cdp(
        cls,
        debug_port: int,
        cookies: List[Dict],
        domains: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inject cookies into running Chrome browser using CDP.
        
        Args:
            debug_port: Chrome's remote debugging port
            cookies: List of cookies in EditThisCookie JSON format
            domains: Optional list of domains to filter
            
        Returns:
            Dict with injection result
        """
        if not cookies:
            return {"success": False, "error": "No cookies provided"}
        
        # Filter by domains if specified
        if domains:
            filtered_cookies = []
            for c in cookies:
                domain = c.get("domain", "")
                if any(d in domain or domain in d for d in domains):
                    filtered_cookies.append(c)
            cookies = filtered_cookies
        
        if not cookies:
            return {"success": False, "error": "No cookies match the specified domains"}
        
        try:
            # Connect to Chrome DevTools
            cdp_url = f"http://127.0.0.1:{debug_port}"
            
            async with aiohttp.ClientSession() as session:
                # Get list of targets
                async with session.get(f"{cdp_url}/json") as resp:
                    if resp.status != 200:
                        return {"success": False, "error": f"CDP not available on port {debug_port}"}
                    targets = await resp.json()
                
                if not targets:
                    return {"success": False, "error": "No browser targets found"}
                
                # Find a page target
                page_target = None
                for target in targets:
                    if target.get("type") == "page":
                        page_target = target
                        break
                
                if not page_target:
                    page_target = targets[0]
                
                ws_url = page_target.get("webSocketDebuggerUrl")
                if not ws_url:
                    return {"success": False, "error": "No WebSocket URL available"}
                if "localhost" in ws_url:
                    ws_url = ws_url.replace("localhost", "127.0.0.1")
                
                # Connect via WebSocket
                import websockets
                
                async with websockets.connect(ws_url) as ws:
                    injected = 0
                    msg_id = 1  # Use simple integer counter for CDP message IDs
                    
                    for cookie in cookies:
                        # Build CDP cookie object
                        cdp_cookie = {
                            "name": cookie.get("name", ""),
                            "value": cookie.get("value", ""),
                            "domain": cookie.get("domain", ""),
                            "path": cookie.get("path", "/"),
                            "secure": cookie.get("secure", False),
                            "httpOnly": cookie.get("httpOnly", False),
                        }
                        
                        # Handle expiration
                        exp = cookie.get("expirationDate") or cookie.get("expires")
                        if exp:
                            cdp_cookie["expires"] = float(exp)
                        
                        # Handle sameSite
                        same_site = cookie.get("sameSite")
                        if same_site:
                            if same_site.lower() == "lax":
                                cdp_cookie["sameSite"] = "Lax"
                            elif same_site.lower() == "strict":
                                cdp_cookie["sameSite"] = "Strict"
                            elif same_site.lower() in ("none", "no_restriction"):
                                cdp_cookie["sameSite"] = "None"
                        
                        # Set URL for the cookie - required for domain cookies
                        domain = cookie.get("domain", "")
                        if domain.startswith("."):
                            domain = domain[1:]
                        scheme = "https" if cookie.get("secure") else "http"
                        cdp_cookie["url"] = f"{scheme}://{domain}/"
                        
                        # Send CDP command with integer ID
                        cmd = {
                            "id": msg_id,
                            "method": "Network.setCookie",
                            "params": cdp_cookie
                        }
                        msg_id += 1
                        
                        await ws.send(json.dumps(cmd))
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                            result = json.loads(response)
                            if result.get("result", {}).get("success", False):
                                injected += 1
                            else:
                                logger.warning(f"Failed to set cookie {cookie.get('name')}: {result}")
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout setting cookie {cookie.get('name')}")
                    
                    logger.info(f"Injected {injected}/{len(cookies)} cookies via CDP port {debug_port}")
                    
                    # Navigate to YouTube to activate cookies
                    if injected > 0:
                        navigate_cmd = {
                            "id": msg_id + 1,
                            "method": "Page.navigate",
                            "params": {"url": "https://www.youtube.com"}
                        }
                        await ws.send(json.dumps(navigate_cmd))
                        try:
                            await asyncio.wait_for(ws.recv(), timeout=5.0)
                            logger.info("Navigated to YouTube after cookie injection")
                        except asyncio.TimeoutError:
                            pass
                    
                    return {
                        "success": True,
                        "imported": injected,
                        "total": len(cookies),
                        "message": f"Injected {injected} cookies"
                    }
                    
        except Exception as e:
            logger.error(f"Failed to inject cookies via CDP: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    def inject_cookies_sync(
        cls,
        debug_port: int,
        cookies: List[Dict],
        domains: List[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for inject_cookies_via_cdp."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            cls.inject_cookies_via_cdp(debug_port, cookies, domains)
        )
    
    @classmethod
    def import_google_cookies(cls, debug_port: int, cookies: List[Dict]) -> Dict[str, Any]:
        """
        Import Google/YouTube cookies for authentication via CDP.
        Filters to only Google-related domains.
        """
        google_domains = [
            "google.com",
            "youtube.com",
            "googlevideo.com",
            "gstatic.com",
            "googleapis.com"
        ]
        
        return cls.inject_cookies_sync(
            debug_port=debug_port,
            cookies=cookies,
            domains=google_domains
        )


# Keep old method for backward compatibility - but it won't work with modern Chrome
class CookieManagerLegacy:
    """Legacy SQLite-based cookie import - doesn't work with encrypted Chrome cookies."""
    
    @classmethod
    def get_cookies_db_path(cls, profile_path: Path) -> Path:
        """Get path to Chrome's Cookies database."""
        return profile_path / "Default" / "Cookies"
    
    # ... rest of old implementation kept for reference


# Singleton instance
cookie_manager = CookieManager()
