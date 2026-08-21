"""
Browser interaction simulator for human-like behavior.
Uses Chrome DevTools Protocol (CDP) to simulate mouse movements, clicks, and scrolls.
"""

import asyncio
import random
import httpx
from typing import Optional, Dict, Any, List
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BrowserInteraction:
    """
    Simulates human-like browser interactions via Chrome DevTools Protocol.
    This helps ensure YouTube videos play properly by mimicking user presence.
    """
    
    @staticmethod
    def _normalize_ws_url(url: Optional[str]) -> Optional[str]:
        """Normalize WebSocket URL to use 127.0.0.1 instead of localhost for Windows compatibility."""
        if url and "localhost" in url:
            return url.replace("localhost", "127.0.0.1")
        return url

    @classmethod
    async def navigate_to_url(cls, debug_port: int, url: str) -> bool:
        """Navigate the browser tab to the specified URL using CDP."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                page_target = next((t for t in targets if t.get("type") == "page"), None)
                if not page_target:
                    return False
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return False
                
                import websockets
                import json
                async with websockets.connect(ws_url) as ws:
                    await ws.send(json.dumps({"id": 1001, "method": "Page.enable"}))
                    await ws.send(json.dumps({
                        "id": 1002,
                        "method": "Page.navigate",
                        "params": {"url": url}
                    }))
                    await asyncio.sleep(0.5)
                    return True
        except Exception as e:
            logger.error(f"CDP navigate error: {e}")
            return False

    @classmethod
    async def inject_stealth_patches(cls, debug_port: int) -> Dict[str, Any]:
        """
        Inject JavaScript to hide automation indicators from websites.
        This should be called immediately after browser launch.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            
        Returns:
            Dict with injection results
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                
                page_target = next((t for t in targets if t.get("type") == "page"), None)
                if not page_target:
                    return {"success": False, "error": "No page target found"}
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return {"success": False, "error": "No WebSocket URL"}
                
                import websockets
                import json as json_module
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(json_module.dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = json_module.loads(response)
                            if data.get("id") == message["id"]:
                                return data
                    
                    # Stealth JavaScript to hide automation
                    stealth_script = """
                        // Hide webdriver flag
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        
                        // Fake plugins
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        
                        // Fake languages
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en']
                        });
                        
                        // Hide automation flags in Chrome
                        if (window.chrome) {
                            window.chrome.runtime = {
                                connect: () => {},
                                sendMessage: () => {}
                            };
                        }
                        
                        // Override permissions query
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                        );
                        
                        console.log('Stealth patches applied');
                    """
                    
                    # Inject on page load
                    await send_cdp("Page.addScriptToEvaluateOnNewDocument", {
                        "source": stealth_script
                    })
                    
                    # Also run now on current page
                    await send_cdp("Runtime.evaluate", {
                        "expression": stealth_script,
                        "returnByValue": True
                    })
                    
                    logger.debug(f"Stealth patches injected on port {debug_port}")
                    return {"success": True, "message": "Stealth patches applied"}
                    
        except Exception as e:
            logger.warning(f"Failed to inject stealth patches: {e}")
            return {"success": False, "error": str(e)}
    
    
    @classmethod
    async def detect_bot_check(cls, debug_port: int) -> Dict[str, Any]:
        """
        Detect if YouTube is showing the 'confirm you're not a bot' page.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            
        Returns:
            Dict with: detected (bool), message (str if bot check found)
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                
                page_target = None
                current_url = ""
                for target in targets:
                    if target.get("type") == "page":
                        page_target = target
                        current_url = target.get("url", "")
                        break
                
                if not page_target:
                    return {"detected": False}
                
                # Check URL for bot verification patterns
                bot_url_patterns = [
                    "google.com/sorry",
                    "accounts.google.com/v3/signin",
                    "consent.youtube.com",
                    "accounts.google.com/ServiceLogin"
                ]
                for pattern in bot_url_patterns:
                    if pattern in current_url:
                        logger.warning(f"Bot check detected via URL: {current_url}")
                        return {"detected": True, "phrase": f"URL: {pattern}"}
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return {"detected": False}
                
                import websockets
                import json as json_module
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(json_module.dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = json_module.loads(response)
                            if data.get("id") == message["id"]:
                                return data
                    
                    # Check for bot verification page indicators
                    bot_check_script = """
                    (function() {
                        const bodyText = document.body ? document.body.innerText : '';
                        const pageTitle = document.title || '';
                        
                        // Check for common bot detection text
                        const botPhrases = [
                            "confirm that you're not a bot",
                            "confirm you're not a bot",
                            "Sign in to confirm",
                            "unusual traffic",
                            "automated requests",
                            "Before you continue",
                            "I'm not a robot",
                            "Verify you are human"
                        ];
                        
                        for (const phrase of botPhrases) {
                            if (bodyText.toLowerCase().includes(phrase.toLowerCase())) {
                                return { detected: true, phrase: phrase };
                            }
                        }
                        
                        // Check for Google's captcha iframe
                        const captchaFrame = document.querySelector('iframe[src*="recaptcha"]');
                        if (captchaFrame) {
                            return { detected: true, phrase: 'recaptcha iframe' };
                        }
                        
                        // Check for specific Google consent divs
                        const consentDiv = document.querySelector('[data-consent-page]');
                        if (consentDiv) {
                            return { detected: true, phrase: 'consent page' };
                        }
                        
                        // Check for YouTube video overlay bot check
                        const ytOverlay = document.querySelector('.ytp-error-content, .ytp-error-content-wrap');
                        if (ytOverlay && ytOverlay.innerText) {
                            const overlayText = ytOverlay.innerText.toLowerCase();
                            if (overlayText.includes('sign in') || overlayText.includes('confirm') || overlayText.includes('bot')) {
                                return { detected: true, phrase: 'video overlay: ' + overlayText.substring(0, 50) };
                            }
                        }
                        
                        // Check for sign-in modal overlay (Commented out to avoid false-positives on guest profiles)
                        // const signInModal = document.querySelector('[aria-label*="Sign in"], .yt-dialog-overlay');
                        // if (signInModal && signInModal.offsetParent !== null) {
                        //     return { detected: true, phrase: 'sign-in modal' };
                        // }
                        
                        // Check if video player shows error
                        const playerError = document.querySelector('.ytp-error');
                        if (playerError) {
                            const errorText = playerError.innerText || '';
                            if (errorText.toLowerCase().includes('sign in') || errorText.toLowerCase().includes('bot')) {
                                return { detected: true, phrase: 'player error: sign in required' };
                            }
                        }
                        
                        return { detected: false };
                    })();
                    """
                    
                    result = await send_cdp("Runtime.evaluate", {
                        "expression": bot_check_script,
                        "returnByValue": True,
                        "awaitPromise": True
                    })
                    
                    check_result = result.get("result", {}).get("result", {}).get("value", {})
                    
                    if check_result.get("detected", False):
                        logger.warning(f"Bot check detected via page content: {check_result.get('phrase')}")
                    
                    return check_result
                    
        except Exception as e:
            logger.debug(f"Bot check detection error: {e}")
            return {"detected": False, "error": str(e)}
    

    @classmethod
    async def simulate_human_presence(
        cls,
        debug_port: int,
        duration_seconds: float = 10,
        interaction_count: int = 5
    ) -> Dict[str, Any]:
        """
        Simulate human-like interactions in the browser.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            duration_seconds: Total duration to spread interactions over
            interaction_count: Number of interaction events to generate
            
        Returns:
            Dict with interaction results
        """
        results = {
            "success": True,
            "interactions": [],
            "errors": []
        }
        
        try:
            # Get the active page/target
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                
                # Find the YouTube page
                page_target = None
                for target in targets:
                    if target.get("type") == "page" and "youtube.com" in target.get("url", ""):
                        page_target = target
                        break
                
                if not page_target:
                    # Fall back to first page
                    page_target = next((t for t in targets if t.get("type") == "page"), None)
                
                if not page_target:
                    results["success"] = False
                    results["errors"].append("No page target found")
                    return results
                
                # Connect to the page via WebSocket
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    results["success"] = False
                    results["errors"].append("No WebSocket URL available")
                    return results
                
                import websockets
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(__import__('json').dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = __import__('json').loads(response)
                            if data.get("id") == message["id"]:
                                return data
                    
                    # Enable input events
                    await send_cdp("Input.enable")
                    
                    # Get page dimensions
                    layout = await send_cdp("Page.getLayoutMetrics")
                    viewport = layout.get("result", {}).get("cssLayoutViewport", {})
                    width = viewport.get("clientWidth", 1280)
                    height = viewport.get("clientHeight", 720)
                    
                    # Calculate delay between interactions
                    delay = duration_seconds / max(interaction_count, 1)
                    
                    for i in range(interaction_count):
                        try:
                            # Mix of moves and scrolls - scrolling makes it look more human
                            action_type = random.choice(["move", "scroll", "scroll", "move"])
                            
                            if action_type == "move":
                                # Random position in sidebar or below video (safe areas)
                                # Avoid center of screen where video player is
                                if random.random() > 0.5:
                                    # Sidebar area (right side)
                                    x = random.randint(int(width * 0.7), max(int(width * 0.7) + 1, width - 50))
                                    y = random.randint(150, max(150, height - 100))
                                else:
                                    # Below video area (comments section)
                                    x = random.randint(100, int(width * 0.6))
                                    y = random.randint(int(height * 0.6), max(int(height * 0.6) + 1, height - 50))
                                
                                await send_cdp("Input.dispatchMouseEvent", {
                                    "type": "mouseMoved",
                                    "x": x,
                                    "y": y,
                                    "button": "none"
                                })
                                results["interactions"].append({"type": "move", "x": x, "y": y})
                                
                            elif action_type == "scroll":
                                # Scroll in comments/sidebar area with visible scroll amount
                                # Position in right side or lower portion of screen
                                x = random.randint(int(width * 0.5), width - 100)
                                y = random.randint(int(height * 0.5), height - 100)
                                
                                # Larger scroll amounts to be visible (mostly scrolling down)
                                scroll_delta = random.choice([100, 150, 200, -50, 250, 300])
                                await send_cdp("Input.dispatchMouseEvent", {
                                    "type": "mouseWheel",
                                    "x": x,
                                    "y": y,
                                    "deltaX": 0,
                                    "deltaY": scroll_delta
                                })
                                results["interactions"].append({"type": "scroll", "delta": scroll_delta, "x": x, "y": y})
                            
                            # Wait before next interaction
                            await asyncio.sleep(delay + random.uniform(-0.2, 0.2))
                            
                        except Exception as e:
                            results["errors"].append(f"Interaction {i} failed: {str(e)}")
                    
                    logger.debug(f"Simulated {len(results['interactions'])} human interactions on port {debug_port}")
                    
        except Exception as e:
            logger.error(f"Error simulating human presence: {e}")
            results["success"] = False
            results["errors"].append(str(e))
        
        return results
    
    @classmethod
    async def click_play_button(cls, debug_port: int) -> Dict[str, Any]:
        """
        Try to click YouTube's play button to start the video.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            
        Returns:
            Dict with result
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                
                page_target = None
                for target in targets:
                    if target.get("type") == "page" and "youtube.com" in target.get("url", ""):
                        page_target = target
                        break
                
                if not page_target:
                    return {"success": False, "error": "No YouTube page found"}
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return {"success": False, "error": "No WebSocket URL"}
                
                import websockets
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(__import__('json').dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = __import__('json').loads(response)
                            if data.get("id") == message["id"]:
                                return data
                    
                    # Try JavaScript to click play - more robust version
                    result = await send_cdp("Runtime.evaluate", {
                        "expression": """
                            (async function() {
                                // Wait for video player to be ready
                                await new Promise(r => setTimeout(r, 1000));
                                
                                let result = [];
                                
                                // 1. Try direct video element play
                                const video = document.querySelector('video');
                                if (video) {
                                    try {
                                        // Mute first to bypass autoplay restrictions
                                        video.muted = true;
                                        await video.play();
                                        video.muted = false;
                                        result.push('played via video.play()');
                                    } catch(e) {
                                        result.push('video.play() failed: ' + e.message);
                                    }
                                }
                                
                                // 2. Click the big central play button overlay
                                const bigPlay = document.querySelector('.ytp-large-play-button');
                                if (bigPlay && bigPlay.offsetParent !== null) {
                                    bigPlay.click();
                                    result.push('clicked big play overlay');
                                }
                                
                                // 3. Click the play/pause button in controls
                                const playBtn = document.querySelector('.ytp-play-button');
                                if (playBtn) {
                                    const isPaused = playBtn.getAttribute('data-title-no-tooltip') === 'Play' ||
                                                     playBtn.getAttribute('title')?.includes('Play');
                                    if (isPaused) {
                                        playBtn.click();
                                        result.push('clicked control play button');
                                    }
                                }
                                
                                // 4. Try clicking the video element itself
                                if (video && video.paused) {
                                    video.click();
                                    result.push('clicked video element');
                                }
                                
                                // 5. Send keyboard shortcut 'k' to toggle play
                                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'k', code: 'KeyK', bubbles: true}));
                                result.push('sent K key');
                                
                                // Check final state
                                await new Promise(r => setTimeout(r, 500));
                                const isPlaying = video && !video.paused;
                                
                                return { actions: result, playing: isPlaying };
                            })();
                        """,
                        "returnByValue": True,
                        "awaitPromise": True
                    })
                    
                    play_result = result.get("result", {}).get("result", {}).get("value", "unknown")
                    logger.info(f"Play button click result: {play_result}")
                    
                    return {"success": True, "result": play_result}
                    
        except Exception as e:
            logger.error(f"Error clicking play button: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    async def ensure_video_playing(cls, debug_port: int, max_attempts: int = 3) -> bool:
        """
        Ensure the YouTube video is actually playing.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            max_attempts: Number of attempts to start playback
            
        Returns:
            True if video is playing
        """
        for attempt in range(max_attempts):
            try:
                # Wait a bit for page to load
                if attempt == 0:
                    await asyncio.sleep(2)
                
                # Try to click play
                click_result = await cls.click_play_button(debug_port)
                
                if click_result.get("success"):
                    # Give it time to start
                    await asyncio.sleep(1)
                    
                    # Simulate some mouse movement to show "human presence"
                    await cls.simulate_human_presence(debug_port, duration_seconds=2, interaction_count=2)
                    
                    return True
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to ensure video playing failed: {e}")
            
            await asyncio.sleep(1)
        
        return False

    @classmethod
    async def handle_youtube_ads(cls, debug_port: int, max_wait_seconds: int = 30) -> Dict[str, Any]:
        """
        Detect and skip YouTube ads. Only waits if an ad is actually detected.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            max_wait_seconds: Maximum time to wait for ads to finish (only if ad detected)
            
        Returns:
            Dict with result: ads_skipped count, or no ad found
        """
        result = {
            "success": True,
            "ads_found": 0,
            "ads_skipped": 0,
            "total_ad_time": 0
        }
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                
                page_target = None
                for target in targets:
                    if target.get("type") == "page" and "youtube.com" in target.get("url", ""):
                        page_target = target
                        break
                
                if not page_target:
                    return {"success": True, "ads_found": 0, "message": "No YouTube page found"}
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return {"success": True, "ads_found": 0, "message": "No WebSocket URL"}
                
                import websockets
                import json as json_module
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(json_module.dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=10)
                            data = json_module.loads(response)
                            if data.get("id") == message["id"]:
                                return data
                    
                    # JavaScript to detect ads and get skip button position
                    ad_detection_script = """
                    (function() {
                        const player = document.querySelector('#movie_player');
                        const hasAdClass = player && player.classList.contains('ad-showing');
                        const adOverlay = document.querySelector('.ad-showing');
                        const adText = document.querySelector('.ytp-ad-text, .ytp-ad-simple-ad-badge');
                        
                        // Find skip button and get its position
                        const selectors = ['.ytp-skip-ad-button', '.ytp-ad-skip-button', '.ytp-ad-skip-button-modern', 'button.ytp-ad-skip-button-slot'];
                        let skipBtn = null;
                        let btnRect = null;
                        
                        for (const sel of selectors) {
                            const btn = document.querySelector(sel);
                            if (btn && btn.offsetParent !== null) {
                                skipBtn = btn;
                                btnRect = btn.getBoundingClientRect();
                                break;
                            }
                        }
                        
                        const isAd = !!(hasAdClass || adOverlay || adText);
                        const canSkip = !!(skipBtn && btnRect && btnRect.width > 0);
                        
                        return { 
                            isAd, 
                            canSkip,
                            skipX: canSkip ? Math.round(btnRect.left + btnRect.width / 2) : 0,
                            skipY: canSkip ? Math.round(btnRect.top + btnRect.height / 2) : 0
                        };
                    })();
                    """
                    
                    # Quick initial check - do 3 fast checks (1.5 seconds total)
                    ad_detected = False
                    for _ in range(3):
                        try:
                            detect_result = await send_cdp("Runtime.evaluate", {
                                "expression": ad_detection_script,
                                "returnByValue": True,
                                "awaitPromise": True
                            })
                            ad_info = detect_result.get("result", {}).get("result", {}).get("value", {})
                            
                            if ad_info.get("isAd", False):
                                ad_detected = True
                                break
                        except:
                            pass
                        await asyncio.sleep(0.5)
                    
                    # If no ad detected in initial check, return immediately
                    if not ad_detected:
                        logger.debug("No ad detected, proceeding with video")
                        return result
                    
                    # Ad is playing - now wait for skip button
                    logger.info("YouTube ad detected, waiting for skip button...")
                    result["ads_found"] = 1
                    
                    start_time = asyncio.get_event_loop().time()
                    
                    while (asyncio.get_event_loop().time() - start_time) < max_wait_seconds:
                        try:
                            detect_result = await send_cdp("Runtime.evaluate", {
                                "expression": ad_detection_script,
                                "returnByValue": True,
                                "awaitPromise": True
                            })
                            ad_info = detect_result.get("result", {}).get("result", {}).get("value", {})
                            
                            # Ad finished on its own
                            if not ad_info.get("isAd", False):
                                logger.info("Ad finished")
                                return result
                            
                            # Skip button available - use REAL mouse click via CDP
                            if ad_info.get("canSkip", False):
                                skip_x = ad_info.get("skipX", 0)
                                skip_y = ad_info.get("skipY", 0)
                                
                                if skip_x > 0 and skip_y > 0:
                                    logger.info(f"Skip button found at ({skip_x}, {skip_y}), clicking...")
                                    
                                    # Move mouse to button
                                    await send_cdp("Input.dispatchMouseEvent", {
                                        "type": "mouseMoved",
                                        "x": skip_x,
                                        "y": skip_y
                                    })
                                    await asyncio.sleep(0.1)
                                    
                                    # Mouse down
                                    await send_cdp("Input.dispatchMouseEvent", {
                                        "type": "mousePressed",
                                        "x": skip_x,
                                        "y": skip_y,
                                        "button": "left",
                                        "clickCount": 1
                                    })
                                    await asyncio.sleep(0.05)
                                    
                                    # Mouse up
                                    await send_cdp("Input.dispatchMouseEvent", {
                                        "type": "mouseReleased",
                                        "x": skip_x,
                                        "y": skip_y,
                                        "button": "left",
                                        "clickCount": 1
                                    })
                                    
                                    result["ads_skipped"] = 1
                                    await asyncio.sleep(1)  # Wait for skip to take effect
                                    
                                    # Verify ad was actually skipped
                                    verify_result = await send_cdp("Runtime.evaluate", {
                                        "expression": ad_detection_script,
                                        "returnByValue": True,
                                        "awaitPromise": True
                                    })
                                    verify_info = verify_result.get("result", {}).get("result", {}).get("value", {})
                                    
                                    if not verify_info.get("isAd", False):
                                        logger.info("Ad skipped successfully!")
                                        return result
                                    else:
                                        logger.warning("Skip click sent but ad still playing, retrying...")
                                        
                        except asyncio.TimeoutError:
                            pass
                        except Exception as e:
                            logger.debug(f"Ad check error: {e}")
                        
                        await asyncio.sleep(0.5)
                    
                    # Timeout waiting for skip - ad might be unskippable
                    logger.info(f"Ad wait complete after {max_wait_seconds}s (unskippable ad)")
                    
        except Exception as e:
            logger.debug(f"Ad handling error (non-critical): {e}")
        
        return result

    @classmethod
    async def simulate_homepage_warmup(cls, debug_port: int) -> bool:
        """
        Navigate to YouTube homepage, browse recommended feed, click a random video,
        and watch it for 10-25 seconds to warm up session cookies.
        """
        logger.info("Starting organic homepage warmup...")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                page_target = next((t for t in targets if t.get("type") == "page"), None)
                if not page_target:
                    return False
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return False
                
                import websockets
                import json as json_module
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(json_module.dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = json_module.loads(response)
                            if data.get("id") == message["id"]:
                                return data

                    # 1. Navigate to YouTube homepage if not already there
                    current_url = page_target.get("url", "")
                    if "youtube.com" not in current_url or current_url.strip() == "https://www.youtube.com/":
                        logger.info("Navigating to YouTube homepage...")
                        await send_cdp("Page.navigate", {"url": "https://www.youtube.com"})
                        await asyncio.sleep(5)  # Wait for homepage to load
                    
                    # 2. Extract a random video link from recommended grid
                    find_link_script = """
                    (function() {
                        var links = Array.from(document.querySelectorAll('a[href*="/watch"]'));
                        links = links.filter(a => a.href && !a.href.includes('/shorts') && a.getBoundingClientRect().height > 0);
                        if (links.length === 0) return null;
                        var randomLink = links[Math.floor(Math.random() * links.length)];
                        return randomLink.href;
                    })()
                    """
                    link_res = await send_cdp("Runtime.evaluate", {
                        "expression": find_link_script,
                        "returnByValue": True
                    })
                    random_url = link_res.get("result", {}).get("result", {}).get("value")
                    
                    if random_url:
                        logger.info(f"Organic warmup: Clicking recommended video URL: {random_url}")
                        await send_cdp("Page.navigate", {"url": random_url})
                        
                        # Watch for 10-25 seconds
                        watch_time = random.uniform(10.0, 25.0)
                        logger.info(f"Warmup: Watching random video for {watch_time:.1f} seconds...")
                        
                        # Simulate basic human movements during warmup
                        elapsed = 0
                        while elapsed < watch_time:
                            if elapsed > 0 and elapsed % 8 == 0:
                                # Scroll slightly
                                scroll_expr = f"window.scrollBy(0, {random.randint(-150, 150)});"
                                await send_cdp("Runtime.evaluate", {"expression": scroll_expr})
                            await asyncio.sleep(1)
                            elapsed += 1
                            
                        logger.info("Warmup complete.")
                        return True
                    else:
                        logger.warning("No recommended videos found on homepage.")
        except Exception as e:
            logger.debug(f"Warmup failed: {e}")
        return False

    @classmethod
    async def search_and_click_video(cls, debug_port: int, keywords: str, target_channel: str, target_title: str) -> bool:
        """
        Type keywords into search bar, hit search, scroll down to locate target video,
        matching by channel name/uploader or title, and click it.
        """
        logger.info(f"Starting organic search for keywords: '{keywords}'")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                targets_response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                targets = targets_response.json()
                page_target = next((t for t in targets if t.get("type") == "page"), None)
                if not page_target:
                    return False
                
                ws_url = cls._normalize_ws_url(page_target.get("webSocketDebuggerUrl"))
                if not ws_url:
                    return False
                
                import websockets
                import json as json_module
                
                async with websockets.connect(ws_url) as ws:
                    msg_id = 1
                    async def send_cdp(method: str, params: dict = None) -> dict:
                        nonlocal msg_id
                        message = {"id": msg_id, "method": method, "params": params or {}}
                        msg_id += 1
                        await ws.send(json_module.dumps(message))
                        while True:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            data = json_module.loads(response)
                            if data.get("id") == message["id"]:
                                return data

                    # 1. Ensure we are on YouTube homepage/search page
                    current_url = page_target.get("url", "")
                    if "youtube.com" not in current_url:
                        await send_cdp("Page.navigate", {"url": "https://www.youtube.com"})
                        await asyncio.sleep(4)
                    
                    # 2. Type keywords into search input
                    type_script = f"""
                    (function() {{
                        var input = document.querySelector('input#search') || document.querySelector('input[name="search_query"]');
                        if (!input) return false;
                        input.focus();
                        input.value = "";
                        input.value = "{keywords}";
                        input.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }})()
                    """
                    await send_cdp("Runtime.evaluate", {"expression": type_script})
                    await asyncio.sleep(random.uniform(0.5, 1.5))  # Replicate thinking time
                    
                    # 3. Submit search query
                    click_search_script = """
                    (function() {
                        var input = document.querySelector('input#search') || document.querySelector('input[name="search_query"]');
                        if (input) {
                            input.focus();
                            
                            // Dispatch Enter key events to trigger YouTube's JS handlers
                            var keydown = new KeyboardEvent('keydown', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 });
                            var keypress = new KeyboardEvent('keypress', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 });
                            var keyup = new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 });
                            
                            input.dispatchEvent(keydown);
                            input.dispatchEvent(keypress);
                            input.dispatchEvent(keyup);
                            
                            // Force form submit event and call submit() as fallback
                            var form = input.closest('form') || document.querySelector('form#search-form');
                            if (form) {
                                var submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                                if (form.dispatchEvent(submitEvent)) {
                                    form.submit();
                                }
                                return true;
                            }
                        }
                        
                        // Final fallback: click the search button
                        var btn = document.querySelector('button#search-icon-legacy') || document.querySelector('form#search-form button') || document.querySelector('#search-icon-legacy');
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        return false;
                    })()
                    """
                    await send_cdp("Runtime.evaluate", {"expression": click_search_script})
                    await asyncio.sleep(4)  # Wait for search results
                    
                    # 4. Scroll down and try to match target video (up to 5 scroll attempts)
                    for scroll_attempt in range(6):
                        logger.info(f"Scanning search results page (Scroll attempt {scroll_attempt}/5)...")
                        
                        # Find and click video card match
                        channel_esc = target_channel.replace('"', '\\"')
                        title_esc = target_title.replace('"', '\\"')
                        
                        click_video_script = f"""
                        (function() {{
                            var items = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-grid-video-renderer, ytd-rich-grid-media'));
                            var targetChannel = "{channel_esc}";
                            var targetTitle = "{title_esc}";
                            
                            for (var item of items) {{
                                var channelEl = item.querySelector('#channel-info, #channel-name, .ytd-channel-name, #byline-container');
                                var channelText = channelEl ? channelEl.textContent.trim().toLowerCase() : "";
                                
                                var titleEl = item.querySelector('#video-title, a#video-title-link, h3');
                                var titleText = titleEl ? titleEl.textContent.trim().toLowerCase() : "";
                                
                                var channelMatch = targetChannel && channelText.includes(targetChannel.toLowerCase());
                                var titleMatch = targetTitle && titleText.includes(targetTitle.toLowerCase());
                                
                                if (channelMatch || titleMatch) {{
                                    var link = item.querySelector('a#video-title-link') || item.querySelector('a[href*="/watch"]');
                                    if (link) {{
                                        link.click();
                                        return {{ success: true, title: titleText, channel: channelText }};
                                    }}
                                }}
                            }}
                            return {{ success: false, count: items.length }};
                        }})()
                        """
                        
                        match_res = await send_cdp("Runtime.evaluate", {
                            "expression": click_video_script,
                            "returnByValue": True
                        })
                        match_info = match_res.get("result", {}).get("result", {}).get("value", {})
                        
                        if match_info.get("success"):
                            logger.info(f"✅ Found and clicked target video: '{match_info.get('title')}' by '{match_info.get('channel')}'")
                            return True
                        
                        # Not found, scroll down
                        logger.info("Target video not visible in current view, scrolling down...")
                        await send_cdp("Runtime.evaluate", {"expression": "window.scrollBy(0, 750);"})
                        await asyncio.sleep(2)
                        
                    logger.warning("Target video not found in search results.")
        except Exception as e:
            logger.debug(f"Search navigation failed: {e}")
        return False
