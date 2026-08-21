"""
Browser service for Chrome profile operations.
"""

import json
import os
import asyncio
import random
import subprocess
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.config import settings
from app.utils.logger import setup_logger
from app.services.proxy_manager import ProxyManager

logger = setup_logger(__name__)


class BrowserService:
    """Service for managing Chrome browser profiles."""
    
    # Comprehensive OS-specific fingerprint profiles for anti-detection
    # Each profile contains consistent, matching data for realistic browser simulation
    OS_FINGERPRINT_PROFILES = {
        "windows": {
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            ],
            "platform": "Win32",
            "resolutions": [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1536, "height": 864},
                {"width": 2560, "height": 1440},
                {"width": 1440, "height": 900},
            ],
            "webgl_vendors": ["Google Inc. (Intel)", "Google Inc. (NVIDIA)", "Google Inc. (AMD)"],
            "webgl_renderers": [
                "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            ],
            "hardware_concurrency": [4, 6, 8, 12, 16],
            "device_memory": [8, 16, 32],
            "max_touch_points": 0,
            "languages": ["en-US", "en-GB", "en-CA"],
        },
        "macos": {
            "user_agents": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            ],
            "platform": "MacIntel",
            "resolutions": [
                {"width": 1440, "height": 900},
                {"width": 1680, "height": 1050},
                {"width": 2560, "height": 1600},
                {"width": 1920, "height": 1080},
                {"width": 2880, "height": 1800},
            ],
            "webgl_vendors": ["Apple Inc."],
            "webgl_renderers": [
                "Apple M1",
                "Apple M2",
                "Apple M3",
                "Apple GPU",
                "Intel Inc. -- Intel(R) Iris(TM) Plus Graphics",
            ],
            "hardware_concurrency": [8, 10, 12, 16],
            "device_memory": [8, 16, 24, 32],
            "max_touch_points": 0,
            "languages": ["en-US", "en-GB", "en-AU"],
        },
        "linux": {
            "user_agents": [
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            ],
            "platform": "Linux x86_64",
            "resolutions": [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 2560, "height": 1440},
                {"width": 1680, "height": 1050},
            ],
            "webgl_vendors": ["Intel", "NVIDIA Corporation", "AMD"],
            "webgl_renderers": [
                "Mesa Intel(R) UHD Graphics 630 (CFL GT2)",
                "NVIDIA GeForce GTX 1080/PCIe/SSE2",
                "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, DRM 3.49, 6.1.0-18-amd64)",
            ],
            "hardware_concurrency": [4, 6, 8, 12, 16],
            "device_memory": [8, 16, 32],
            "max_touch_points": 0,
            "languages": ["en-US", "en-GB"],
        },
        "android": {
            "user_agents": [
                "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
                "Mozilla/5.0 (Linux; Android 14; OnePlus 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
            ],
            "platform": "Linux armv81",
            "resolutions": [
                {"width": 412, "height": 915},
                {"width": 393, "height": 873},
                {"width": 360, "height": 800},
                {"width": 384, "height": 854},
                {"width": 428, "height": 926},
            ],
            "webgl_vendors": ["Qualcomm", "ARM", "Imagination Technologies"],
            "webgl_renderers": [
                "Adreno (TM) 740",
                "Adreno (TM) 730",
                "Mali-G715 MC7",
                "Mali-G710 MC10",
            ],
            "hardware_concurrency": [8],
            "device_memory": [8, 12, 16],
            "max_touch_points": 5,
            "languages": ["en-US", "en-GB"],
        },
    }
    
    # OS platform weights for random selection
    # NOTE: For best detection resistance, use the SAME platform as your host machine
    # Since you're on macOS, we weight heavily toward macOS to avoid inconsistencies
    OS_PLATFORM_WEIGHTS = {
        "windows": 0.40,  # 40% Windows
        "macos": 0.50,    # 50% macOS (matches your host)
        "linux": 0.10,    # 10% Linux
        "android": 0.00,  # 0% Android (disabled - causes detection on desktop)
    }
    

    # Chrome paths by OS
    CHROME_PATHS = {
        "darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "linux": "/usr/bin/google-chrome",
        "win32": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    }
    
    # Running browser processes
    _running_browsers: Dict[str, subprocess.Popen] = {}
    
    @classmethod
    def get_chrome_path(cls) -> str:
        """Get Chrome executable path for current OS."""
        import sys
        platform = sys.platform
        return cls.CHROME_PATHS.get(platform, cls.CHROME_PATHS["darwin"])
    
    @classmethod
    def create_profile_directory(cls, device_id: int, profile_name: str) -> Path:
        """
        Create a directory for the Chrome profile.
        
        Args:
            device_id: Device ID
            profile_name: Profile name
            
        Returns:
            Path to the created profile directory
        """
        profile_path = settings.PROFILES_DIR / f"device_{device_id}" / profile_name
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Create First Run file to skip Chrome's first run experience
        first_run_file = profile_path / "First Run"
        first_run_file.touch()
        
        # Create Local State to skip popups and enable developer mode for extensions
        local_state = {
            "browser": {
                "enabled_labs_experiments": [],
                "has_seen_welcome_page": True
            },
            "profile": {
                "created_by_version": "120.0.0.0",
                "default_content_setting_values": {}
            },
            "extensions": {
                "ui": {
                    "developer_mode": True
                }
            }
        }
        local_state_file = profile_path / "Local State"
        with open(local_state_file, "w") as f:
            json.dump(local_state, f)
        
        # Create Default profile subfolder
        default_profile = profile_path / "Default"
        default_profile.mkdir(exist_ok=True)
        
        # Create Preferences to skip all popups and welcome screens
        preferences = {
            "browser": {
                "has_seen_welcome_page": True,
                "check_default_browser": False,
                "default_browser_setting_enabled": False
            },
            "signin": {
                "allowed": False,
                "allowed_on_next_startup": False
            },
            "profile": {
                "default_content_setting_values": {
                    "notifications": 2,  # Block notifications
                    "geolocation": 2,    # Block geolocation
                }
            },
            "autofill": {
                "profile_enabled": False,
                "credit_card_enabled": False
            },
            "credentials_enable_service": False,
            "credentials_enable_autosignin": False,
            "translate": {
                "enabled": False
            },
            "savefile": {
                "default_directory": str(profile_path / "Downloads")
            },
            "extensions": {
                "ui": {
                    "developer_mode": True
                }
            }
        }
        prefs_file = default_profile / "Preferences"
        with open(prefs_file, "w") as f:
            json.dump(preferences, f)
        
        logger.info(f"Created profile directory: {profile_path}")
        return profile_path
    
    @classmethod
    def generate_fingerprint(cls, os_platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a unique browser fingerprint for the profile.
        
        Args:
            os_platform: Optional specific OS to use (windows, macos, linux, android).
                        If None, randomly selects based on OS_PLATFORM_WEIGHTS.
        
        Returns:
            Dictionary containing fingerprint data including os_platform
        """
        # Select OS platform if not specified
        if os_platform is None or os_platform not in cls.OS_FINGERPRINT_PROFILES:
            platforms = list(cls.OS_PLATFORM_WEIGHTS.keys())
            weights = list(cls.OS_PLATFORM_WEIGHTS.values())
            os_platform = random.choices(platforms, weights=weights, k=1)[0]
        
        # Get the profile for selected OS
        profile = cls.OS_FINGERPRINT_PROFILES[os_platform]
        
        # Select random values from the profile
        resolution = random.choice(profile["resolutions"])
        webgl_vendor = random.choice(profile["webgl_vendors"])
        webgl_renderer = random.choice(profile["webgl_renderers"])
        user_agent = random.choice(profile["user_agents"])
        
        # Extract Chrome version from user agent (e.g., "Chrome/124.0.0.0" -> "124")
        import re
        version_match = re.search(r'Chrome/(\d+)', user_agent)
        browser_version = version_match.group(1) if version_match else "124"
        
        # Common timezones
        timezones = ["America/New_York", "America/Los_Angeles", "America/Chicago", "Europe/London", "Europe/Paris"]
        
        fingerprint = {
            "os_platform": os_platform,
            "browser_version": browser_version,
            "user_agent": user_agent,
            "screen_width": resolution["width"],
            "screen_height": resolution["height"],
            "language": random.choice(profile["languages"]),
            "timezone": random.choice(timezones),
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            "platform": profile["platform"],
            "hardware_concurrency": random.choice(profile["hardware_concurrency"]),
            "device_memory": random.choice(profile["device_memory"]),
            "max_touch_points": profile["max_touch_points"],
            "is_mobile": os_platform == "android",
        }
        
        logger.info(f"Generated fingerprint for OS: {os_platform}, Chrome v{browser_version}")
        return fingerprint
    
    @classmethod
    def save_fingerprint(cls, profile_path: Path, fingerprint: Dict[str, Any]) -> None:
        """
        Save fingerprint data to profile directory.
        
        Args:
            profile_path: Path to profile directory
            fingerprint: Fingerprint data
        """
        fingerprint_file = profile_path / "fingerprint.json"
        with open(fingerprint_file, "w") as f:
            json.dump(fingerprint, f, indent=2)
        logger.info(f"Saved fingerprint to: {fingerprint_file}")
    
    @classmethod
    def load_fingerprint(cls, profile_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load fingerprint data from profile directory.
        
        Args:
            profile_path: Path to profile directory
            
        Returns:
            Fingerprint data or None if not found
        """
        fingerprint_file = profile_path / "fingerprint.json"
        if fingerprint_file.exists():
            with open(fingerprint_file, "r") as f:
                return json.load(f)
        return None
    
    @classmethod
    def delete_profile_directory(cls, profile_path: str) -> bool:
        """
        Delete a profile directory and all its contents.
        
        Args:
            profile_path: Path to profile directory
            
        Returns:
            True if deleted successfully
        """
        path = Path(profile_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.info(f"Deleted profile directory: {path}")
            return True
        return False
    
    @classmethod
    def create_proxy_auth_extension(cls, profile_path: Path, username: str, password: str) -> Optional[Path]:
        """
        Create a Chrome extension for automatic proxy authentication.
        Skips creation if extension already exists with same credentials.
        
        Args:
            profile_path: Path to profile directory
            username: Proxy username
            password: Proxy password
            
        Returns:
            Path to the extension directory
        """
        ext_dir = profile_path / "proxy_auth_ext"
        config_file = ext_dir / "config.json"
        
        # Check if extension already exists with same credentials
        if ext_dir.exists() and config_file.exists():
            try:
                with open(config_file, "r") as f:
                    existing_config = json.load(f)
                if existing_config.get("username") == username and existing_config.get("password") == password:
                    logger.info(f"Proxy auth extension already exists with correct credentials for {username}")
                    return ext_dir
            except Exception:
                pass  # Will recreate if config read fails
        
        ext_dir.mkdir(exist_ok=True)
        
        # Create manifest.json (Manifest V2 for proper blocking auth support)
        manifest = {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Proxy Auth",
            "description": "Auto-authenticate proxy",
            "permissions": [
                "proxy",
                "webRequest",
                "webRequestBlocking",
                "<all_urls>"
            ],
            "background": {
                "scripts": ["background.js"],
                "persistent": True
            }
        }
        
        with open(ext_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Save config for future checks
        with open(config_file, "w") as f:
            json.dump({"username": username, "password": password}, f)
        
        # Create background.js with synchronous blocking callback (Manifest V2)
        background_js = f'''// Proxy authentication handler - Manifest V2
var config = {{
  username: "{username}",
  password: "{password}"
}};

chrome.webRequest.onAuthRequired.addListener(
  function(details) {{
    console.log("Proxy auth required for:", details.challenger);
    return {{
      authCredentials: {{
        username: config.username,
        password: config.password
      }}
    }};
  }},
  {{ urls: ["<all_urls>"] }},
  ["blocking"]
);

console.log("Proxy Auth Extension loaded for user:", config.username);
'''
        
        with open(ext_dir / "background.js", "w") as f:
            f.write(background_js)
        
        logger.info(f"Created/updated proxy auth extension at: {ext_dir}")
        return ext_dir
    
    @classmethod
    def create_proxy_auth_zip(cls, profile_path: Path, username: str, password: str) -> Optional[Path]:
        """
        Create a packed (ZIP) Chrome extension for Selenium WebDriver.
        
        Args:
            profile_path: Path to profile directory
            username: Proxy username
            password: Proxy password
            
        Returns:
            Path to the extension ZIP file
        """
        zip_path = profile_path / "proxy_auth.zip"
        
        # Create manifest
        manifest_content = json.dumps({
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Proxy Auth",
            "description": "Auto-authenticate proxy",
            "permissions": [
                "proxy",
                "webRequest",
                "webRequestBlocking",
                "<all_urls>"
            ],
            "background": {
                "scripts": ["background.js"],
                "persistent": True
            }
        }, indent=2)
        
        # Create background.js
        background_js = f'''var config = {{
  username: "{username}",
  password: "{password}"
}};

chrome.webRequest.onAuthRequired.addListener(
  function(details) {{
    return {{
      authCredentials: {{
        username: config.username,
        password: config.password
      }}
    }};
  }},
  {{ urls: ["<all_urls>"] }},
  ["blocking"]
);
'''
        
        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_content)
            zf.writestr("background.js", background_js)
        
        logger.info(f"Created proxy auth extension ZIP at: {zip_path}")
        return zip_path
    
    @classmethod
    def launch_browser(cls, profile_path: str, url: str = "about:blank", proxy: dict = None) -> Dict[str, Any]:
        """
        Launch Chrome browser with the specified profile.
        
        Args:
            profile_path: Path to profile directory
            url: URL to open (default: about:blank)
            proxy: Optional proxy dict with keys: ip, port, username, password, proxy_type
            
        Returns:
            Dict with status and process info
        """
        path = Path(profile_path)
        if not path.exists():
            # Search in settings.PROFILES_DIR directly or in subfolders (e.g. device_X)
            matches = list(settings.PROFILES_DIR.glob(f"**/{path.name}"))
            if matches and matches[0].exists():
                path = matches[0]
            else:
                return {"success": False, "error": f"Profile path does not exist: {profile_path}"}
        
        # Load fingerprint for user agent
        fingerprint = cls.load_fingerprint(path)
        # Default fallback user agent if no fingerprint exists (match macOS host)
        default_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
        user_agent = fingerprint.get("user_agent", default_ua) if fingerprint else default_ua
        
        # Chrome flags to disable popups, first-run experience, and reduce detection
        chrome_flags = [
            f"--user-data-dir={path}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-translate",
            "--disable-sync",
            "--disable-background-networking",
            f"--user-agent={user_agent}",
            "--disable-infobars",
            "--disable-notifications",
            "--start-maximized",
            # Allow video autoplay without user interaction
            "--autoplay-policy=no-user-gesture-required",
            "--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies",
            # Anti-detection is handled via JavaScript injection in BrowserInteraction.inject_stealth_patches()
            # Removed command-line flags that trigger warning banners
            "--disable-dev-shm-usage",  # For stability
            # Disable WebRTC IP leak
            "--disable-webrtc",
            "--enforce-webrtc-ip-permission-check",
            # Disable web security for cross-origin (careful with this)
            # "--disable-web-security",  # Uncomment if needed
            # Additional stealth flags
            "--disable-logging",
            "--log-level=3",  # Suppress console logs
            "--silent-debugger-extension-api",
            # Disable automation detection features
            "--disable-extensions-except=",
            "--disable-plugins-discovery",
        ]
        
        # Add remote debugging port for CDP (used for cookie injection)
        # Use a unique port per profile based on a base port + hash
        profile_name = path.name
        base_port = 9222
        port_offset = abs(hash(profile_name)) % 1000
        debug_port = base_port + port_offset
        chrome_flags.append(f"--remote-debugging-port={debug_port}")
        
        # Add proxy configuration if provided
        if proxy:
            proxy_ip = proxy.get("ip")
            proxy_port = proxy.get("port")
            proxy_type = proxy.get("proxy_type", "HTTP").lower()
            proxy_user = proxy.get("username")
            proxy_pass = proxy.get("password")
            
            if proxy_ip and proxy_port:
                # If the proxy is authenticated (has username/password), ALWAYS route it through our
                # local high-performance proxy forwarder server. This makes Chrome connect without credentials,
                # completely preventing any popup dialogs on startup.
                if proxy_user and proxy_pass:
                    local_port = ProxyManager.start_forwarder(profile_name, proxy)
                    if local_port:
                        chrome_flags.append(f"--proxy-server=http://127.0.0.1:{local_port}")
                        logger.info(f"Using local proxy forwarder on port {local_port} for authenticated proxy {proxy_ip}:{proxy_port}")
                    else:
                        chrome_flags.append(f"--proxy-server={proxy_type}://{proxy_ip}:{proxy_port}")
                        logger.warning(f"Local proxy forwarder failed to start, falling back to direct proxy connection")
                else:
                    # Non-authenticated proxy
                    if proxy_type == "socks5":
                        chrome_flags.append(f"--proxy-server=socks5://{proxy_ip}:{proxy_port}")
                    else:
                        chrome_flags.append(f"--proxy-server=http://{proxy_ip}:{proxy_port}")
                
                logger.info(f"Configured proxy: {proxy_ip}:{proxy_port} ({proxy_type})")
        
        chrome_flags.append(url)
        
        try:
            chrome_path = cls.get_chrome_path()
            cmd = [chrome_path] + chrome_flags
            
            # Launch browser process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Track running browser with debug port
            cls._running_browsers[profile_name] = {
                "process": process,
                "debug_port": debug_port,
                "cookies_injected": False,  # Track if cookies have been injected
                "cdp_auth_task": None,
                "cdp_stop_event": None
            }
            
            logger.info(f"Launched browser for profile: {profile_name} (PID: {process.pid}, CDP port: {debug_port})")
            
            return {
                "success": True,
                "profile_name": profile_name,
                "pid": process.pid,
                "debug_port": debug_port,
                "message": f"Browser launched for {profile_name}",
                "proxy_configured": proxy is not None
            }
            
        except FileNotFoundError:
            return {"success": False, "error": "Chrome executable not found"}
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return {"success": False, "error": str(e)}
     
    @classmethod
    def close_browser(cls, profile_name: str) -> Dict[str, Any]:
        """
        Close a running browser by profile name.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Dict with status
        """
        # Stop proxy forwarder if running
        ProxyManager.stop_forwarder(profile_name)
        
        # Force-kill any lingering Chrome processes associated with this profile on macOS/Linux
        import sys
        if sys.platform != "win32":
            try:
                import subprocess
                # Find PIDs of processes matching the profile name (excluding the grep commands and this python process)
                cmd = f"ps aux | grep -i '{profile_name}' | grep -v grep | awk '{{print $2}}'"
                pids_out = subprocess.check_output(cmd, shell=True).decode().strip()
                if pids_out:
                    pids = pids_out.split('\n')
                    for pid in pids:
                        pid = pid.strip()
                        if pid:
                            subprocess.run(["kill", "-9", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            logger.info(f"Force-killed process {pid} for profile {profile_name}")
            except Exception as ke:
                logger.debug(f"Failed to force-kill lingering processes for {profile_name}: {ke}")
        
        if profile_name in cls._running_browsers:
            browser_info = cls._running_browsers[profile_name]
            
            # Cancel native CDP auth task if running
            if isinstance(browser_info, dict):
                stop_event = browser_info.get("cdp_stop_event")
                if stop_event:
                    stop_event.set()
                cdp_task = browser_info.get("cdp_auth_task")
                if cdp_task:
                    cdp_task.cancel()
            
            process = browser_info.get("process") if isinstance(browser_info, dict) else browser_info
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    try:
                        process.kill()
                    except:
                        pass
            del cls._running_browsers[profile_name]
            logger.info(f"Closed browser for profile: {profile_name}")
            return {"success": True, "message": f"Browser closed for {profile_name}"}
        
        return {"success": True, "message": f"Lingering browser processes terminated for {profile_name}"}
    
    @classmethod
    def get_running_browsers(cls) -> List[str]:
        """Get list of running browser profile names."""
        return list(cls._running_browsers.keys())
    
    @classmethod
    def are_cookies_injected(cls, profile_name: str) -> bool:
        """Check if cookies have already been injected for this browser session."""
        if profile_name in cls._running_browsers:
            return cls._running_browsers[profile_name].get("cookies_injected", False)
        return False
    
    @classmethod
    def mark_cookies_injected(cls, profile_name: str) -> None:
        """Mark that cookies have been injected for this browser session."""
        if profile_name in cls._running_browsers:
            cls._running_browsers[profile_name]["cookies_injected"] = True
            logger.info(f"Marked cookies as injected for profile: {profile_name}")

    @classmethod
    def close_all_browsers(cls) -> None:
        """Close all active browsers and force-kill any remaining automation Chrome instances."""
        running = list(cls._running_browsers.keys())
        for profile_name in running:
            try:
                cls.close_browser(profile_name)
            except Exception as e:
                logger.error(f"Error closing browser for {profile_name}: {e}")

        # Also terminate any Chrome process that was launched with --user-data-dir referencing profiles_data
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'chrome' in (proc.info.get('name') or '').lower() or 'chromium' in (proc.info.get('name') or '').lower():
                        cmdline = " ".join(proc.info.get('cmdline') or [])
                        if 'profiles_data' in cmdline:
                            proc.kill()
                            logger.info(f"Killed orphan profile browser PID {proc.info.get('pid')}")
                except Exception:
                    pass
        except Exception:
            pass
