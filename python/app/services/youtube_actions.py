"""
YouTube Actions Service - Handles liking videos and posting comments.
Uses Chrome DevTools Protocol (CDP) to interact with the browser.
"""

import asyncio
import random
import json
from typing import Dict, Any, List, Optional
import httpx

from app.utils.logger import setup_logger
from app.services.browser_service import BrowserService

logger = setup_logger(__name__)

from app.config import settings

def get_laravel_endpoint(endpoint: str) -> str:
    """Construct full Laravel API endpoint URL from settings."""
    base = (settings.LARAVEL_API_URL or "http://youtube.test/api").rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    clean_ep = endpoint.lstrip("/").replace("api/", "")
    return f"{base}/{clean_ep}"

# Random positive comments pool
COMMENT_POOL = [
    "Great video! Really enjoyed watching this 🔥",
    "This is amazing content, keep it up! 👏",
    "Loved every second of this video! ❤️",
    "Incredible work, subscribed! 🙌",
    "This is exactly what I was looking for, thanks! 💯",
    "Wow, this is so helpful! Thank you! 🎉",
    "Best video on this topic I've seen! 👍",
    "Quality content as always! Keep going! 💪",
    "This deserves way more views! Sharing this! 📢",
    "You're an inspiration! Amazing video! ✨",
    "I learned so much from this, thank you! 📚",
    "Perfect explanation, very well done! 👌",
    "This made my day! Awesome content! 😊",
    "Can't believe this is free content! So good! 💎",
    "Instant subscribe! This is gold! 🏆",
    "Finally someone who explains it properly! 🙏",
    "Outstanding work! Blown away! 🤯",
    "This is pure quality, respect! 💜",
    "Bookmarking this for later! So valuable! 📌",
    "You've gained a fan today! Great job! 🌟",
    "Such a creative approach, love it! 🎨",
    "This is exactly the content we need! 👊",
    "Phenomenal video, shared with my friends! 📲",
    "The production quality is insane! 🎬",
    "You're underrated, deserve millions of views! 📈",
]


class YouTubeActions:
    """Service for performing YouTube actions using CDP."""
    
    @classmethod
    def get_random_comment(cls) -> str:
        """Get a random comment from the pool."""
        return random.choice(COMMENT_POOL)
    
    @classmethod
    def get_cdp_port_for_profile(cls, profile_name: str) -> Optional[int]:
        """Get the CDP debug port for a running profile."""
        if profile_name in BrowserService._running_browsers:
            browser_info = BrowserService._running_browsers[profile_name]
            return browser_info.get("debug_port")
        return None
    
    @classmethod
    async def open_url_in_browser(cls, debug_port: int, url: str) -> Dict[str, Any]:
        """
        Navigate the browser to a URL via CDP.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            url: URL to navigate to
            
        Returns:
            Dict with success status
        """
        js = f"""
        (async () => {{
            window.location.href = '{url}';
            return {{ success: true, url: '{url}' }};
        }})();
        """
        return await cls.execute_js_in_browser(debug_port, js)
    
    @classmethod
    async def wait_for_cdp_ready(cls, debug_port: int, max_retries: int = 5) -> bool:
        """Wait for CDP to be ready and accessible."""
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"http://127.0.0.1:{debug_port}/json")
                    if response.status_code == 200:
                        targets = response.json()
                        if targets:
                            logger.info(f"CDP ready on port {debug_port} (attempt {attempt + 1})")
                            return True
            except Exception as e:
                logger.debug(f"CDP not ready yet (attempt {attempt + 1}): {e}")
            
            await asyncio.sleep(1)
        
        return False
    
    @classmethod
    async def execute_js_in_browser(cls, debug_port: int, javascript: str, max_retries: int = 3) -> Dict[str, Any]:
        """Execute JavaScript in the browser via CDP WebSocket with retries."""
        import websockets
        
        # First ensure CDP is accessible
        if not await cls.wait_for_cdp_ready(debug_port):
            return {"success": False, "error": f"CDP not accessible on port {debug_port}"}
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Get targets
                async with httpx.AsyncClient(timeout=10) as client:
                    targets_resp = await client.get(f"http://127.0.0.1:{debug_port}/json")
                    targets = targets_resp.json()
                    
                    page_target = None
                    for target in targets:
                        if target.get("type") == "page" and "youtube" in target.get("url", "").lower():
                            page_target = target
                            break
                    
                    if not page_target:
                        for target in targets:
                            if target.get("type") == "page":
                                page_target = target
                                break
                    
                    if not page_target:
                        return {"success": False, "error": "No YouTube page found"}
                    
                    ws_url = page_target.get("webSocketDebuggerUrl")
                    if not ws_url:
                        return {"success": False, "error": "No WebSocket URL"}
                    if "localhost" in ws_url:
                        ws_url = ws_url.replace("localhost", "127.0.0.1")
                
                # Connect via WebSocket and execute JS
                async with websockets.connect(ws_url, close_timeout=5) as ws:
                    msg_id = random.randint(1, 999999)
                    command = {
                        "id": msg_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": javascript,
                            "returnByValue": True,
                            "awaitPromise": True
                        }
                    }
                    
                    await ws.send(json.dumps(command))
                    
                    # Wait for response with timeout
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=60)
                        result = json.loads(response)
                        
                        if result.get("id") == msg_id:
                            logger.debug(f"CDP Response: {json.dumps(result, indent=2)[:500]}")
                            
                            if "error" in result:
                                return {"success": False, "error": str(result["error"])}
                            
                            # Parse the result - CDP structure is result.result.value
                            cdp_result = result.get("result", {})
                            
                            # Check for exception
                            if cdp_result.get("exceptionDetails"):
                                exc = cdp_result["exceptionDetails"]
                                error_msg = exc.get("exception", {}).get("description", "JavaScript exception")
                                logger.error(f"JS Exception: {error_msg}")
                                return {"success": False, "error": error_msg}
                            
                            # Get the actual result value
                            inner_result = cdp_result.get("result", {})
                            value = inner_result.get("value")
                            
                            logger.info(f"CDP inner_result: {inner_result}")
                            
                            if value is not None:
                                return {"success": True, "value": value}
                            
                            # If no value, return the type info
                            return {"success": False, "error": f"No value returned, type: {inner_result.get('type')}"}
                            
            except asyncio.TimeoutError:
                last_error = "Timeout waiting for JS response"
                logger.warning(f"CDP timeout (attempt {attempt + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"CDP error (attempt {attempt + 1}): {e}")
            
            # Wait before retry
            await asyncio.sleep(1)
        
        return {"success": False, "error": last_error or "All attempts failed"}
    
    @classmethod
    async def like_video(cls, profile_name: str, video_url: str) -> Dict[str, Any]:
        """Like a YouTube video using CDP."""
        debug_port = cls.get_cdp_port_for_profile(profile_name)
        if not debug_port:
            logger.error(f"No CDP port found for profile {profile_name}")
            return {"success": False, "error": f"No CDP port found for profile {profile_name}"}
        
        logger.info(f"Attempting to like video via CDP port {debug_port}")
        
        # JavaScript to click the like button
        like_js = """
        (async function() {
            try {
                // Wait a moment for elements to be ready
                await new Promise(r => setTimeout(r, 2000));
                
                // Find like button - YouTube uses various selectors
                let likeButton = null;
                
                // Try the new YouTube layout - look for the like button in the actions
                const allButtons = document.querySelectorAll('button');
                for (const btn of allButtons) {
                    const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                    // Match "like this video" or just "like" but not "dislike"
                    if ((ariaLabel.includes('like') && !ariaLabel.includes('dislike')) ||
                        ariaLabel.includes('i like this')) {
                        likeButton = btn;
                        break;
                    }
                }
                
                // Fallback: try specific YouTube selectors
                if (!likeButton) {
                    const selectors = [
                        'like-button-view-model button',
                        'ytd-toggle-button-renderer[is-icon-button] button',
                        '#top-level-buttons-computed button',
                        'ytd-segmented-like-dislike-button-renderer button'
                    ];
                    for (const sel of selectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            likeButton = btn;
                            break;
                        }
                    }
                }
                
                if (!likeButton) {
                    return { success: false, error: 'Like button not found on page' };
                }
                
                // Check if already liked (aria-pressed="true" means liked)
                const isLiked = likeButton.getAttribute('aria-pressed') === 'true';
                if (isLiked) {
                    return { success: true, message: 'Video already liked', already_liked: true };
                }
                
                // Scroll the like button into view
                likeButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                await new Promise(r => setTimeout(r, 500));
                
                // Click the like button
                likeButton.click();
                
                await new Promise(r => setTimeout(r, 1000));
                
                // Verify the like was successful
                const isNowLiked = likeButton.getAttribute('aria-pressed') === 'true';
                if (isNowLiked) {
                    return { success: true, message: 'Video liked successfully', newly_liked: true };
                } else {
                    return { success: true, message: 'Click sent, status unknown' };
                }
            } catch (e) {
                return { success: false, error: e.toString() };
            }
        })();
        """
        
        result = await cls.execute_js_in_browser(debug_port, like_js)
        logger.info(f"Like JS result: {result}")
        
        if result.get("success") and result.get("value"):
            return result["value"]
        
        return {"success": False, "error": result.get("error", "Unknown error")}
    
    @classmethod
    async def post_comment(cls, profile_name: str, video_url: str, comment: str = None) -> Dict[str, Any]:
        """Post a comment on a YouTube video using CDP."""
        debug_port = cls.get_cdp_port_for_profile(profile_name)
        if not debug_port:
            return {"success": False, "error": f"No CDP port found for profile {profile_name}"}
        
        if not comment:
            comment = cls.get_random_comment()
        
        # Escape the comment for JavaScript
        comment_escaped = json.dumps(comment)[1:-1]  # Use JSON encoding for safety
        
        logger.info(f"Attempting to post comment via CDP port {debug_port}")
        
        # JavaScript to post a comment
        comment_js = f"""
        (async function() {{
            try {{
                const comment = "{comment_escaped}";
                
                // Scroll down multiple times to load comments section
                for (let i = 0; i < 3; i++) {{
                    window.scrollBy(0, 400);
                    await new Promise(r => setTimeout(r, 500));
                }}
                
                await new Promise(r => setTimeout(r, 2000));
                
                // Find the comment placeholder - try multiple selectors
                let placeholder = document.querySelector('#simplebox-placeholder');
                if (!placeholder) {{
                    placeholder = document.querySelector('ytd-comment-simplebox-renderer #placeholder-area');
                }}
                if (!placeholder) {{
                    placeholder = document.querySelector('[id*="simplebox"] [id*="placeholder"]');
                }}
                
                if (!placeholder) {{
                    // Scroll more and try again
                    window.scrollTo(0, 800);
                    await new Promise(r => setTimeout(r, 2000));
                    placeholder = document.querySelector('#simplebox-placeholder');
                }}
                
                if (!placeholder) {{
                    return {{ success: false, error: 'Comment placeholder not found after scrolling' }};
                }}
                
                // Click the placeholder to activate comment input
                placeholder.click();
                await new Promise(r => setTimeout(r, 2000));
                
                // Find the comment input (contenteditable div)
                let input = document.querySelector('#contenteditable-root');
                if (!input) {{
                    input = document.querySelector('div[contenteditable="true"]');
                }}
                
                if (!input) {{
                    return {{ success: false, error: 'Comment input field not found' }};
                }}
                
                // Focus the input
                input.focus();
                
                // Clear existing content using selection
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                
                // Type the comment using document.execCommand (bypasses Trusted Types)
                for (const char of comment) {{
                    document.execCommand('insertText', false, char);
                    await new Promise(r => setTimeout(r, 30 + Math.random() * 50));
                }}
                
                await new Promise(r => setTimeout(r, 1500));
                
                // Find submit button
                let submitBtn = document.querySelector('#submit-button button');
                if (!submitBtn) {{
                    submitBtn = document.querySelector('ytd-button-renderer#submit-button button');
                }}
                if (!submitBtn) {{
                    // Try to find by aria-label
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {{
                        if (btn.getAttribute('aria-label')?.toLowerCase().includes('comment')) {{
                            submitBtn = btn;
                            break;
                        }}
                    }}
                }}
                
                if (!submitBtn) {{
                    return {{ success: false, error: 'Submit button not found' }};
                }}
                
                // Check if button is enabled
                if (submitBtn.disabled || submitBtn.getAttribute('aria-disabled') === 'true') {{
                    return {{ success: false, error: 'Submit button is disabled - comment may be too short' }};
                }}
                
                // Click submit
                submitBtn.click();
                await new Promise(r => setTimeout(r, 3000));
                
                return {{ success: true, message: 'Comment submitted successfully' }};
            }} catch (e) {{
                return {{ success: false, error: e.toString() }};
            }}
        }})();
        """
        
        result = await cls.execute_js_in_browser(debug_port, comment_js)
        logger.info(f"Comment JS result: {result}")
        
        if result.get("success") and result.get("value"):
            response = result["value"]
            if response.get("success"):
                response["comment"] = comment
            return response
        
        return {"success": False, "error": result.get("error", "Unknown error"), "comment": comment}

    @classmethod
    async def subscribe_channel(cls, profile_name: str, video_url: str) -> Dict[str, Any]:
        """Subscribe to the channel of the video page using CDP."""
        debug_port = cls.get_cdp_port_for_profile(profile_name)
        if not debug_port:
            logger.error(f"No CDP port found for profile {profile_name}")
            return {"success": False, "error": f"No CDP port found for profile {profile_name}"}
        
        logger.info(f"Attempting to subscribe to channel via CDP port {debug_port}")
        
        # JavaScript to click the subscribe button
        subscribe_js = """
        (async function() {
            try {
                // Wait a moment for elements to be ready
                await new Promise(r => setTimeout(r, 2000));
                
                // Find subscribe button
                let subButton = null;
                
                // Search buttons by text content
                const allButtons = document.querySelectorAll('button');
                for (const btn of allButtons) {
                    const text = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                    const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                    if (text === 'subscribe' || text === 'join' || ariaLabel.includes('subscribe to')) {
                        subButton = btn;
                        break;
                    }
                }
                
                // Fallback selectors
                if (!subButton) {
                    const selectors = [
                        'ytd-subscribe-button-renderer button',
                        'yt-button-shape button[aria-label*="subscribe"]',
                        '#subscribe-button button',
                        '.ytd-subscribe-button-renderer button'
                    ];
                    for (const sel of selectors) {
                        const btn = document.querySelector(sel);
                        if (btn) {
                            subButton = btn;
                            break;
                        }
                    }
                }
                
                if (!subButton) {
                    // Try to find any element with text subscribe
                    const elements = document.querySelectorAll('*');
                    for (const el of elements) {
                        if (el.children.length === 0) {
                            const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                            if (text === 'subscribe') {
                                subButton = el;
                                break;
                            }
                        }
                    }
                }
                
                if (!subButton) {
                    return { success: false, error: 'Subscribe button not found on page' };
                }
                
                // Check if already subscribed
                const buttonText = (subButton.innerText || subButton.textContent || '').trim().toLowerCase();
                const ariaLabel = (subButton.getAttribute('aria-label') || '').toLowerCase();
                const isSubscribed = buttonText.includes('subscribed') || 
                                     ariaLabel.includes('unsubscribe') || 
                                     subButton.classList.contains('subscribed') ||
                                     subButton.getAttribute('subscribed') === 'true';
                                     
                if (isSubscribed) {
                    return { success: true, message: 'Already subscribed to channel', already_subscribed: true };
                }
                
                // Scroll the subscribe button into view
                subButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                await new Promise(r => setTimeout(r, 500));
                
                // Click the subscribe button
                subButton.click();
                
                // Wait for state change / network request
                await new Promise(r => setTimeout(r, 4000));
                
                // Fetch the button again (it might have re-rendered)
                let subButtonAfter = null;
                const allButtonsAfter = document.querySelectorAll('button');
                for (const btn of allButtonsAfter) {
                    const text = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                    const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                    if (text === 'subscribe' || text === 'subscribed' || text === 'unsubscribe' || ariaLabel.includes('subscribe to') || ariaLabel.includes('unsubscribe from')) {
                        subButtonAfter = btn;
                        break;
                    }
                }
                
                if (!subButtonAfter) {
                    return { success: false, error: 'Subscribe button vanished after click' };
                }
                
                const textAfter = (subButtonAfter.innerText || subButtonAfter.textContent || '').trim().toLowerCase();
                const ariaLabelAfter = (subButtonAfter.getAttribute('aria-label') || '').toLowerCase();
                const isSubscribedAfter = textAfter.includes('subscribed') || 
                                          textAfter.includes('unsubscribe') || 
                                          ariaLabelAfter.includes('unsubscribe') ||
                                          subButtonAfter.classList.contains('subscribed') ||
                                          subButtonAfter.getAttribute('subscribed') === 'true';
                                          
                if (isSubscribedAfter) {
                    return { success: true, message: 'Subscribed to channel successfully', newly_subscribed: true };
                } else {
                    // Check if sign-in dialog popped up
                    const dialogs = document.querySelectorAll('ytd-modal-with-renderer, tp-yt-paper-dialog, ytd-popup-container');
                    let modalOpened = false;
                    for (const dlg of dialogs) {
                        if (dlg.offsetHeight > 0 && dlg.offsetWidth > 0) {
                            modalOpened = true;
                            break;
                        }
                    }
                    if (modalOpened) {
                        return { success: false, error: 'Sign-in prompt appeared. Account is not logged in.' };
                    }
                    return { success: false, error: 'Click sent, but button state did not change to Subscribed' };
                }
            } catch (e) {
                return { success: false, error: e.toString() };
            }
        })();
        """
        
        result = await cls.execute_js_in_browser(debug_port, subscribe_js)
        logger.info(f"Subscribe JS result: {result}")
        
        if result.get("success") and result.get("value"):
            return result["value"]
        
        return {"success": False, "error": result.get("error", "Unknown error")}

    @classmethod
    async def report_subscription_to_laravel(
        cls,
        campaign_id: int,
        profile_name: str,
        status: str,
        error_message: str = None
    ) -> Dict[str, Any]:
        """
        Report subscription outcome (success/failure) to Laravel API.
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "campaign_id": campaign_id,
                    "profile_name": profile_name,
                    "status": status,  # 'subscribed' or 'failed'
                }
                if error_message:
                    payload["error_message"] = error_message
                
                response = await client.post(
                    get_laravel_endpoint("campaigns/record-subscription"),
                    json=payload,
                )
                
                if response.status_code == 200:
                    logger.info(f"Reported subscription status ({status}) for campaign {campaign_id} (profile: {profile_name})")
                    return {"success": True, "data": response.json()}
                else:
                    logger.warning(f"Failed to report subscription: {response.status_code} - {response.text}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error reporting subscription to Laravel: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def report_action_to_laravel(
        cls,
        campaign_id: int,
        profile_name: str,
        action_type: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Report an action to Laravel API.
        
        Args:
            campaign_id: Campaign ID
            profile_name: Profile that performed the action
            action_type: Type of action ('like', 'comment', 'view')
            metadata: Additional data (comment_text, already_liked, watch_duration, etc.)
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "campaign_id": campaign_id,
                    "profile_name": profile_name,
                    "action_type": action_type,
                }
                
                # Add metadata fields
                if metadata:
                    if "comment_text" in metadata:
                        payload["comment_text"] = metadata["comment_text"]
                    if "already_liked" in metadata:
                        payload["already_liked"] = metadata["already_liked"]
                    if "watch_duration" in metadata:
                        payload["watch_duration_seconds"] = metadata["watch_duration"]
                    if "watch_percentage" in metadata:
                        payload["watch_percentage"] = metadata["watch_percentage"]
                
                response = await client.post(
                    get_laravel_endpoint("campaigns/action"),
                    json=payload,
                )
                
                if response.status_code == 200:
                    logger.info(f"Reported {action_type} action for campaign {campaign_id} (profile: {profile_name})")
                    return {"success": True, "data": response.json()}
                else:
                    logger.warning(f"Failed to report action: {response.status_code} - {response.text}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error reporting action to Laravel: {e}")
            return {"success": False, "error": str(e)}


# Convenience function for bulk campaign actions
async def perform_campaign_actions(
    campaign_id: int,
    campaign_type: str,
    profiles: List[Dict[str, Any]],
    video_url: str
) -> List[Dict[str, Any]]:
    """Perform campaign actions for multiple profiles."""
    results = []
    
    for profile in profiles:
        profile_name = profile.get("name") or profile.get("profile_name")
        result = {"profile_name": profile_name, "actions": {}}
        
        try:
            if campaign_type in ['likes', 'likes_comments']:
                like_result = await YouTubeActions.like_video(profile_name, video_url)
                result["actions"]["like"] = like_result
                
                # Report like action (even if already liked)
                await YouTubeActions.report_action_to_laravel(
                    campaign_id, profile_name, "like",
                    metadata={"already_liked": like_result.get("already_liked", False)}
                )
            
            if campaign_type in ['comments', 'likes_comments']:
                if campaign_type == 'likes_comments':
                    await asyncio.sleep(random.uniform(2, 4))
                
                comment_result = await YouTubeActions.post_comment(profile_name, video_url)
                result["actions"]["comment"] = comment_result
                
                if comment_result.get("success"):
                    await YouTubeActions.report_action_to_laravel(
                        campaign_id, profile_name, "comment",
                        metadata={"comment_text": comment_result.get("comment")}
                    )
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"Error performing action for {profile_name}: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        results.append(result)
    
    return results
