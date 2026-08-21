"""
Profile management API endpoints.
"""

import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.profile import ProfileCreate, ProfileResponse, ProfileData
from app.models.response import APIResponse
from app.services.profile_service import profile_service
from app.services.browser_service import BrowserService
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class LaunchRequest(BaseModel):
    """Request model for launching browser."""
    profile_path: str = Field(..., description="Path to profile directory")
    url: str = Field(default="about:blank", description="URL to open")
    proxy: Optional[dict] = Field(default=None, description="Proxy config: {ip, port, username, password, proxy_type}")
    google_cookies: Optional[List[dict]] = Field(default=None, description="Google account cookies to import")


class BulkLaunchRequest(BaseModel):
    """Request model for launching multiple browsers."""
    profiles: List[dict] = Field(..., description="List of {profile_path, url, proxy, google_cookies}")



class CloseRequest(BaseModel):
    """Request model for closing browser."""
    profile_name: str = Field(..., description="Profile name to close")


class BulkDeleteRequest(BaseModel):
    """Request for bulk deletion."""
    profile_paths: List[str] = Field(..., description="List of profile paths to delete")


class VideoMetadataRequest(BaseModel):
    """Request model for video metadata."""
    video_url: str = Field(..., description="YouTube video URL")


@router.post("/video/metadata")
async def get_video_metadata(request: VideoMetadataRequest):
    """
    Fetch YouTube video metadata (title, duration, uploader, thumbnail, views, likes).
    """
    from app.services.video_watcher import VideoWatcher
    try:
        metadata = await VideoWatcher.get_video_metadata(request.video_url)
        return metadata
    except Exception as e:
        logger.error(f"Error fetching metadata for {request.video_url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=ProfileResponse)
async def create_profiles(request: ProfileCreate):
    """
    Create Chrome automation profiles.
    
    This endpoint creates the specified number of profiles for a device,
    generates unique fingerprints, and returns the profile data to be
    stored in Laravel.
    """
    logger.info(f"Received create request: {request.count} profiles for device {request.device_id}")
    
    try:
        result = profile_service.create_profiles(request)
        logger.info(f"Successfully created {result.count} profiles")
        return result
    except Exception as e:
        logger.error(f"Failed to create profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=APIResponse)
async def list_profiles(device_id: Optional[int] = Query(None, description="Filter by device ID")):
    """List all profiles, optionally filtered by device."""
    try:
        profiles = profile_service.list_profiles(device_id)
        return APIResponse(
            success=True,
            message=f"Found {len(profiles)} profile(s)",
            data=[p.model_dump() for p in profiles]
        )
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/launch", response_model=APIResponse)
async def launch_browser(request: LaunchRequest):
    """
    Launch Chrome browser with the specified profile.
    
    The browser will open with all popups, login prompts, and
    first-run experience disabled. If google_cookies are provided,
    they will be injected via CDP after the browser launches.
    """
    import asyncio
    from app.services.cookie_manager import CookieManager
    
    logger.info(f"Launching browser for profile: {request.profile_path}")
    
    # Launch browser first
    result = BrowserService.launch_browser(request.profile_path, request.url, request.proxy)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Inject Google cookies via CDP if provided (only if not already injected in this session)
    profile_name = result.get("profile_name", "")
    if request.google_cookies and result.get("debug_port"):
        # Check if cookies were already injected in this browser session
        if BrowserService.are_cookies_injected(profile_name):
            logger.info(f"Cookies already injected for profile {profile_name}, skipping...")
            result["cookies_injected"] = "skipped (already done)"
        else:
            # Wait for browser to be ready (CDP needs a moment)
            await asyncio.sleep(2)
            
            debug_port = result["debug_port"]
            cookie_result = await CookieManager.inject_cookies_via_cdp(
                debug_port=debug_port,
                cookies=request.google_cookies,
                domains=["google.com", "youtube.com"]
            )
            
            if cookie_result.get("success"):
                logger.info(f"Injected {cookie_result.get('imported', 0)} Google cookies via CDP port {debug_port}")
                result["cookies_injected"] = cookie_result.get("imported", 0)
                # Mark cookies as injected for this session
                BrowserService.mark_cookies_injected(profile_name)
            else:
                logger.warning(f"Failed to inject cookies: {cookie_result.get('error')}")
                result["cookies_error"] = cookie_result.get("error")
    
    return APIResponse(
        success=True,
        message=result["message"],
        data=result
    )



@router.post("/launch-bulk", response_model=APIResponse)
async def launch_browsers_bulk(request: BulkLaunchRequest):
    """Launch multiple browsers at once. Injects cookies via CDP after launch."""
    import asyncio
    from app.services.cookie_manager import CookieManager
    
    results = []
    for profile in request.profiles:
        profile_path = profile.get("profile_path", "")
        google_cookies = profile.get("google_cookies")
        
        # Launch browser
        result = BrowserService.launch_browser(
            profile_path,
            profile.get("url", "about:blank"),
            profile.get("proxy")
        )
        
        # Inject cookies via CDP after launch if provided (only if not already injected)
        profile_name = result.get("profile_name", "")
        if result.get("success") and google_cookies and result.get("debug_port"):
            if BrowserService.are_cookies_injected(profile_name):
                logger.info(f"Cookies already injected for profile {profile_name}, skipping...")
                result["cookies_injected"] = "skipped (already done)"
            else:
                await asyncio.sleep(2)  # Wait for browser to be ready
                cookie_result = await CookieManager.inject_cookies_via_cdp(
                    debug_port=result["debug_port"],
                    cookies=google_cookies,
                    domains=["google.com", "youtube.com"]
                )
                if cookie_result.get("success"):
                    result["cookies_injected"] = cookie_result.get("imported", 0)
                    logger.info(f"Injected {cookie_result.get('imported', 0)} cookies for {profile_path}")
                    BrowserService.mark_cookies_injected(profile_name)
        
        results.append(result)
    
    success_count = sum(1 for r in results if r.get("success"))
    
    return APIResponse(
        success=True,
        message=f"Launched {success_count}/{len(request.profiles)} browsers",
        data=results
    )




@router.post("/close", response_model=APIResponse)
async def close_browser(request: CloseRequest):
    """Close a running browser by profile name."""
    logger.info(f"Closing browser for profile: {request.profile_name}")
    
    result = BrowserService.close_browser(request.profile_name)
    
    return APIResponse(
        success=result["success"],
        message=result.get("message", result.get("error", "Unknown")),
        data=result
    )


class BulkCloseRequest(BaseModel):
    """Request model for closing multiple browsers."""
    profile_names: List[str] = Field(..., description="List of profile names to close")


@router.post("/close-bulk", response_model=APIResponse)
async def close_browsers_bulk(request: BulkCloseRequest):
    """Close multiple running browsers at once."""
    results = []
    closed = 0
    
    for profile_name in request.profile_names:
        result = BrowserService.close_browser(profile_name)
        results.append(result)
        if result.get("success"):
            closed += 1
    
    return APIResponse(
        success=True,
        message=f"Closed {closed}/{len(request.profile_names)} browser(s)",
        data={"closed": closed, "results": results}
    )


@router.get("/running", response_model=APIResponse)
async def get_running_browsers():
    """Get list of running browser profile names."""
    running = BrowserService.get_running_browsers()
    return APIResponse(
        success=True,
        message=f"{len(running)} browser(s) running",
        data=running
    )


@router.delete("/bulk", response_model=APIResponse)
async def bulk_delete_profiles(request: BulkDeleteRequest):
    """Bulk delete profiles by their paths."""
    deleted = 0
    failed = []
    
    for path in request.profile_paths:
        success = profile_service.delete_profile(path)
        if success:
            deleted += 1
        else:
            failed.append(path)
    
    return APIResponse(
        success=True,
        message=f"Deleted {deleted}/{len(request.profile_paths)} profiles",
        data={"deleted": deleted, "failed": failed}
    )


class ProxyTestRequest(BaseModel):
    """Request model for testing proxy."""
    ip: str
    port: int
    username: str
    password: str
    proxy_type: str = "SOCKS5"


class BulkProxyTestRequest(BaseModel):
    """Request for testing multiple proxies."""
    proxies: List[dict] = Field(..., description="List of proxy configs to test")


@router.post("/test-proxy", response_model=APIResponse)
async def test_proxy(request: ProxyTestRequest):
    """Test if a proxy is working by making a request through it."""
    import httpx
    
    proxy_type = request.proxy_type.lower()
    if proxy_type == "socks5":
        proxy_url = f"socks5://{request.username}:{request.password}@{request.ip}:{request.port}"
    else:
        proxy_url = f"http://{request.username}:{request.password}@{request.ip}:{request.port}"
    
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15.0) as client:
            response = await client.get("https://api.ipify.org?format=json")
            if response.status_code == 200:
                data = response.json()
                return APIResponse(
                    success=True,
                    message="Proxy is working",
                    data={"status": "working", "external_ip": data.get("ip")}
                )
            else:
                return APIResponse(
                    success=False,
                    message=f"Proxy returned status {response.status_code}",
                    data={"status": "error"}
                )
    except Exception as e:
        logger.error(f"Proxy test failed: {e}")
        return APIResponse(
            success=False,
            message=str(e),
            data={"status": "expired"}
        )


@router.post("/test-proxies-bulk", response_model=APIResponse)
async def test_proxies_bulk(request: BulkProxyTestRequest):
    """Test multiple proxies at once."""
    import httpx
    import asyncio
    
    async def test_single(proxy: dict) -> dict:
        proxy_type = proxy.get("proxy_type", "SOCKS5").lower()
        ip = proxy.get("ip")
        port = proxy.get("port")
        username = proxy.get("username")
        password = proxy.get("password")
        proxy_id = proxy.get("id")
        
        if proxy_type == "socks5":
            proxy_url = f"socks5://{username}:{password}@{ip}:{port}"
        else:
            proxy_url = f"http://{username}:{password}@{ip}:{port}"
        
        try:
            async with httpx.AsyncClient(proxy=proxy_url, timeout=15.0) as client:
                response = await client.get("https://api.ipify.org?format=json")
                if response.status_code == 200:
                    return {"id": proxy_id, "status": "working", "external_ip": response.json().get("ip")}
                return {"id": proxy_id, "status": "error"}
        except:
            return {"id": proxy_id, "status": "expired"}
    
    # Test all proxies concurrently
    tasks = [test_single(p) for p in request.proxies]
    results = await asyncio.gather(*tasks)
    
    working = sum(1 for r in results if r.get("status") == "working")
    
    return APIResponse(
        success=True,
        message=f"{working}/{len(results)} proxies working",
        data={"results": results, "working": working, "total": len(results)}
    )


class CampaignWatchRequest(BaseModel):
    """Request model for watching campaign videos."""
    campaign_id: int = Field(..., description="Campaign ID")
    campaign_type: str = Field(default="views", description="Type: 'views', 'likes', 'comments', 'likes_comments'")
    profiles: List[dict] = Field(..., description="List of {profile_path, profile_name}")
    video_url: str = Field(..., description="YouTube video URL to watch")
    batch_size: Optional[int] = Field(default=None, description="Batch size for processing (None = auto-detect)")


class CampaignBatchedRequest(BaseModel):
    """Request model for batched campaign execution with launch/watch/close per batch."""
    campaign_id: int = Field(..., description="Campaign ID")
    campaign_type: str = Field(default="views", description="Type: 'views', 'likes', 'comments', 'likes_comments'")
    profiles: List[dict] = Field(..., description="List of {profile_path, profile_name, proxy?}")
    video_url: str = Field(..., description="YouTube video URL to watch")
    batch_size: Optional[int] = Field(default=None, description="Batch size for processing (None = auto-detect)")


@router.post("/campaign/run-batched", response_model=APIResponse)
async def run_campaign_batched(request: CampaignBatchedRequest):
    """
    Run campaign with batched execution: Launch batch -> Watch -> Close -> Repeat.
    This ensures only batch_size profiles are open at any time.
    """
    from app.services.video_watcher import VideoWatcher
    from app.services.youtube_actions import YouTubeActions
    from app.services.campaign_cache import CampaignCache
    from app.services.campaign_config import CampaignConfig
    import random
    
    logger.info(f"Starting BATCHED campaign {request.campaign_id} with {len(request.profiles)} profiles")
    logger.info(f"Video URL: {request.video_url}, Campaign type: {request.campaign_type}")
    
    # If campaign is fully completed in cache, clear it so we can run it fresh
    campaign_status = CampaignCache.get_campaign_status(request.campaign_id)
    if campaign_status and campaign_status.get("pending_profiles", 0) == 0 and campaign_status.get("running_profiles", 0) == 0:
        logger.info(f"Campaign {request.campaign_id} was already fully completed in cache. Clearing cache to start fresh.")
        CampaignCache.clear_campaign(request.campaign_id)

    # If campaign was previously cancelled, restart it first
    if CampaignCache.is_cancelled(request.campaign_id):
        logger.info(f"Campaign {request.campaign_id} was cancelled - auto-restarting")
        CampaignCache.restart_campaign(request.campaign_id)
    
    # Register campaign in cache
    profile_names = [p.get("profile_name", "unknown") for p in request.profiles]
    cache_result = CampaignCache.register_campaign(
        campaign_id=request.campaign_id,
        profile_names=profile_names,
        video_url=request.video_url,
        campaign_type=request.campaign_type,
        batch_size=request.batch_size
    )
    
    # Get only pending profiles
    pending_profile_names = set(cache_result.get("pending_profiles", profile_names))
    profiles_to_process = [p for p in request.profiles if p.get("profile_name") in pending_profile_names]
    
    if not profiles_to_process:
        logger.info(f"All profiles already completed for campaign {request.campaign_id}")
        return APIResponse(
            success=True,
            message="All profiles already completed for this campaign",
            data=CampaignCache.get_campaign_status(request.campaign_id)
        )
    
    # Fetch video duration once
    video_duration = await VideoWatcher.get_video_duration(request.video_url)
    logger.info(f"Video duration: {video_duration} seconds")
    
    # Determine batch size (used as our concurrency limit)
    batch_size = CampaignConfig.get_batch_size(request.batch_size)
    
    # 1. Shuffle profiles randomly to make execution order random!
    random.shuffle(profiles_to_process)
    
    # 2. Create queue and populate it
    queue = asyncio.Queue()
    for p in profiles_to_process:
        await queue.put(p)
        
    launch_lock = asyncio.Lock()
    all_results = []
    
    logger.info(f"Processing {len(profiles_to_process)} profiles via queue worker pool (max concurrent: {batch_size})")
    
    async def process_single_profile(profile: dict) -> dict:
        """Launch, watch, perform actions, and close a single profile."""
        profile_name = profile.get("profile_name", "unknown")
        profile_path = profile.get("profile_path", "")
        proxy = profile.get("proxy")
        
        result_data = {
            "profile_name": profile_name,
            "success": False,
            "actions_performed": {}
        }
        
        try:
            # Check if campaign was cancelled
            if CampaignCache.is_cancelled(request.campaign_id):
                result_data["error"] = "Campaign cancelled"
                return result_data
            
            # Acquire launch lock to stagger browser startup CPU spikes and randomize opening intervals
            async with launch_lock:
                # Force close any existing browser process for this profile first to release locks
                try:
                    BrowserService.close_browser(profile_name)
                    logger.info(f"Force closed existing browser process for {profile_name} before launch")
                except Exception as e:
                    logger.warning(f"Error force closing browser before launch: {e}")
                
                stagger_delay = random.uniform(5.0, 15.0)
                logger.info(f"Staggering launch for {profile_name}: waiting {stagger_delay:.1f}s...")
                await asyncio.sleep(stagger_delay)
                
                # 1. Launch browser with video URL (add autoplay parameter)
                video_url = request.video_url
                if 'youtube.com' in video_url or 'youtu.be' in video_url:
                    # Add autoplay parameter to URL
                    if '?' in video_url:
                        video_url += '&autoplay=1&mute=0'
                    else:
                        video_url += '?autoplay=1&mute=0'
                
                logger.info(f"Launching browser for {profile_name}")
                launch_result = BrowserService.launch_browser(profile_path, video_url, proxy)
            
            if not launch_result.get("success"):
                result_data["error"] = f"Failed to launch: {launch_result.get('error', 'Unknown')}"
                return result_data
            
            debug_port = launch_result.get("debug_port")
            
            # 2. Inject Google cookies if available (helps avoid bot detection)
            google_cookies = profile.get("google_cookies")
            if debug_port and google_cookies:
                try:
                    from app.services.cookie_manager import CookieManager
                    await CookieManager.inject_cookies_via_cdp(
                        debug_port, 
                        google_cookies, 
                        domains=[".google.com", ".youtube.com"]
                    )
                    logger.info(f"Injected Google cookies for {profile_name}")
                except Exception as e:
                    logger.warning(f"Failed to inject Google cookies for {profile_name}: {e}")
            
            # 3. Ensure video starts playing with human-like interactions
            if debug_port:
                try:
                    from app.services.browser_interaction import BrowserInteraction
                    # Wait for browser CDP to be ready
                    await asyncio.sleep(2)
                    # Inject stealth patches to hide automation
                    await BrowserInteraction.inject_stealth_patches(debug_port)
                    # Wait for page to load
                    await asyncio.sleep(2)
                    
                    # Check for bot detection page BEFORE trying to play
                    logger.debug(f"{profile_name}: Checking for bot detection page...")
                    bot_check = await BrowserInteraction.detect_bot_check(debug_port)
                    logger.debug(f"{profile_name}: Bot check result: {bot_check}")
                    if bot_check.get("detected", False):
                        phrase = bot_check.get("phrase", "unknown")
                        logger.warning(f"⚠️ {profile_name}: Bot detection triggered! ({phrase}) - Profile needs Google cookies")
                        result_data["error"] = f"Bot check: {phrase}"
                        result_data["needs_cookies"] = True
                        
                        # Notify Laravel about bot detection
                        try:
                            await VideoWatcher.notify_bot_detection(
                                profile_name=profile_name,
                                campaign_id=request.campaign_id,
                                reason=phrase
                            )
                        except Exception as e:
                            logger.debug(f"Failed to notify Laravel of bot detection: {e}")
                        
                        BrowserService.close_browser(profile_name)
                        return result_data
                    
                    # Click play and simulate human presence
                    await BrowserInteraction.ensure_video_playing(debug_port)
                    
                    # Handle YouTube ads - check for ads and skip if found
                    # Quick check (~1.5s) then wait up to 15s only if ad detected
                    ad_result = await BrowserInteraction.handle_youtube_ads(debug_port, max_wait_seconds=15)
                    if ad_result.get("ads_skipped", 0) > 0:
                        logger.info(f"{profile_name}: Ad skipped")
                        await asyncio.sleep(0.5)
                        await BrowserInteraction.ensure_video_playing(debug_port)
                        
                except Exception as e:
                    logger.warning(f"Human interaction failed for {profile_name}: {e}")
            
            # 4. Calculate watch time (now ad-free!)
            watch_percentage = VideoWatcher.get_random_watch_percentage()
            watch_time = max(5, (video_duration * watch_percentage) / 100 + random.uniform(-2, 2))
            
            logger.info(f"Profile {profile_name}: watching {watch_percentage}% ({int(watch_time)}s of {video_duration}s)")
            
            # 5. Wait for watch time with periodic cancellation check and interactions
            elapsed = 0
            while elapsed < watch_time:
                # Check for cancellation every second
                if CampaignCache.is_cancelled(request.campaign_id):
                    logger.info(f"Campaign cancelled, stopping {profile_name}")
                    result_data["error"] = "Campaign cancelled"
                    BrowserService.close_browser(profile_name)
                    return result_data
                
                # Periodic bot detection check (every 5 seconds)
                if debug_port and elapsed > 0 and elapsed % 5 < 1:
                    try:
                        from app.services.browser_interaction import BrowserInteraction
                        bot_check = await BrowserInteraction.detect_bot_check(debug_port)
                        if bot_check.get("detected", False):
                            phrase = bot_check.get("phrase", "unknown")
                            logger.warning(f"⚠️ {profile_name}: Bot detection during playback! ({phrase})")
                            result_data["error"] = f"Bot check: {phrase}"
                            result_data["needs_cookies"] = True
                            
                            # Notify Laravel about bot detection
                            try:
                                await VideoWatcher.notify_bot_detection(
                                    profile_name=profile_name,
                                    campaign_id=request.campaign_id,
                                    reason=f"During playback: {phrase}"
                                )
                            except Exception as e:
                                logger.debug(f"Failed to notify Laravel of bot detection: {e}")
                            
                            BrowserService.close_browser(profile_name)
                            return result_data
                    except Exception as e:
                        logger.debug(f"Bot check during playback failed: {e}")
                
                # Occasional mouse movement to stay "active"
                if debug_port and elapsed > 0 and elapsed % 10 < 1:
                    try:
                        from app.services.browser_interaction import BrowserInteraction
                        await BrowserInteraction.simulate_human_presence(debug_port, duration_seconds=1, interaction_count=1)
                    except:
                        pass
                
                await asyncio.sleep(min(1, watch_time - elapsed))
                elapsed += 1
            
            # 4. Perform actions based on campaign type
            actions_performed = {}
            
            if request.campaign_type in ['likes', 'likes_comments']:
                try:
                    like_result = await YouTubeActions.like_video(profile_name, request.video_url)
                    actions_performed['like'] = like_result
                    
                    # Report like action to Laravel
                    await YouTubeActions.report_action_to_laravel(
                        campaign_id=request.campaign_id,
                        profile_name=profile_name,
                        action_type="like",
                        metadata={"already_liked": like_result.get("already_liked", False)}
                    )
                except Exception as e:
                    logger.error(f"Failed to perform/report like action: {e}")
                    actions_performed['like'] = {"success": False, "error": str(e)}
            
            if request.campaign_type in ['comments', 'likes_comments']:
                try:
                    if request.campaign_type == 'likes_comments':
                        await asyncio.sleep(random.uniform(2, 4))
                    
                    comment_result = await YouTubeActions.post_comment(profile_name, request.video_url)
                    actions_performed['comment'] = comment_result
                    
                    # Report comment action to Laravel
                    if comment_result.get("success"):
                        await YouTubeActions.report_action_to_laravel(
                            campaign_id=request.campaign_id,
                            profile_name=profile_name,
                            action_type="comment",
                            metadata={"comment_text": comment_result.get("comment")}
                        )
                except Exception as e:
                    logger.error(f"Failed to perform/report comment action: {e}")
                    actions_performed['comment'] = {"success": False, "error": str(e)}
            
            # 5. Report view to Laravel
            view_result = await VideoWatcher.report_view_to_laravel(
                campaign_id=request.campaign_id,
                profile_name=profile_name,
                watch_percentage=watch_percentage
            )
            
            # 6. Close browser
            logger.info(f"Closing browser for {profile_name}")
            close_result = BrowserService.close_browser(profile_name)
            
            result_data["success"] = True
            result_data["watch_time"] = int(watch_time)
            result_data["watch_percentage"] = watch_percentage
            result_data["actions_performed"] = actions_performed
            result_data["view_reported"] = view_result.get("success", False)
            result_data["browser_closed"] = close_result.get("success", False)
            
            # Mark profile as ready for next job
            await VideoWatcher.notify_profile_ready(profile_name)
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error processing {profile_name}: {e}")
            result_data["error"] = str(e)
            # Try to close browser on error
            try:
                BrowserService.close_browser(profile_name)
            except:
                pass
            return result_data

    # Worker function to consume queue items
    async def worker():
        while not queue.empty():
            if CampaignCache.is_cancelled(request.campaign_id):
                break
                
            profile = await queue.get()
            profile_name = profile.get("profile_name", "unknown")
            
            # Mark running in cache
            CampaignCache.mark_profile_running(request.campaign_id, profile_name)
            
            # Run the single profile task
            result = await process_single_profile(profile)
            all_results.append(result)
            
            # Update cache based on result
            if result.get("success"):
                CampaignCache.mark_profile_completed(
                    request.campaign_id, 
                    profile_name,
                    result.get("actions_performed", {})
                )
            else:
                CampaignCache.mark_profile_failed(
                    request.campaign_id, 
                    profile_name, 
                    result.get("error", "Unknown")
                )
                
            queue.task_done()

    # Determine concurrency level
    concurrency_limit = min(batch_size, len(profiles_to_process))
    logger.info(f"Spawning {concurrency_limit} concurrent workers to process {len(profiles_to_process)} profiles")
    
    workers = [asyncio.create_task(worker()) for _ in range(concurrency_limit)]
    await asyncio.gather(*workers)
    
    successful = sum(1 for r in all_results if r.get("success", False))
    
    return APIResponse(
        success=True,
        message=f"Campaign completed: {successful}/{len(all_results)} profiles processed",
        data={
            "campaign_id": request.campaign_id,
            "total_profiles": len(all_results),
            "successful": successful,
            "results": all_results,
            "cache_status": CampaignCache.get_campaign_status(request.campaign_id)
        }
    )


@router.post("/campaign/watch", response_model=APIResponse)
async def watch_campaign_videos(request: CampaignWatchRequest):
    """
    Start watching campaign videos in multiple profiles.
    Fetches REAL video duration from YouTube, each profile watches for a random 20-30%,
    then performs actions (like/comment) based on campaign_type, and reports to Laravel.
    Uses CampaignCache to prevent duplicate processing on restart.
    """
    from app.services.video_watcher import VideoWatcher
    from app.services.youtube_actions import YouTubeActions
    from app.services.campaign_cache import CampaignCache
    import random
    
    logger.info(f"Starting campaign watch for campaign {request.campaign_id} with {len(request.profiles)} profiles")
    logger.info(f"Video URL: {request.video_url}, Campaign type: {request.campaign_type}")
    
    # Register campaign in cache (or resume if already registered)
    profile_names = [p.get("profile_name", "unknown") for p in request.profiles]
    cache_result = CampaignCache.register_campaign(
        campaign_id=request.campaign_id,
        profile_names=profile_names,
        video_url=request.video_url,
        campaign_type=request.campaign_type,
        batch_size=request.batch_size
    )
    
    # Get only pending profiles (skip already completed)
    pending_profile_names = set(cache_result.get("pending_profiles", profile_names))
    profiles_to_process = [p for p in request.profiles if p.get("profile_name") in pending_profile_names]
    
    if not profiles_to_process:
        logger.info(f"All profiles already completed for campaign {request.campaign_id}")
        return APIResponse(
            success=True,
            message="All profiles already completed for this campaign",
            data=CampaignCache.get_campaign_status(request.campaign_id)
        )
    
    logger.info(f"Processing {len(profiles_to_process)} profiles ({len(request.profiles) - len(profiles_to_process)} already completed)")
    
    # Fetch real video duration from YouTube
    video_duration = await VideoWatcher.get_video_duration(request.video_url)
    logger.info(f"Video duration: {video_duration} seconds")
    
    async def watch_for_profile(profile: dict) -> dict:
        """Watch video for a single profile, then perform actions based on campaign type."""
        profile_name = profile.get("profile_name", "unknown")
        profile_path = profile.get("profile_path", "")
        
        result_data = {
            "profile_name": profile_name,
            "video_duration": video_duration,
            "actions_performed": {}
        }
        
        # Get random watch percentage (5-10% as set in video_watcher)
        watch_percentage = VideoWatcher.get_random_watch_percentage()
        watch_time = (video_duration * watch_percentage) / 100
        
        # Add small randomness (+/- 2 seconds) but keep minimum of 5 seconds
        watch_time += random.randint(-2, 2)
        watch_time = max(5, watch_time)  # Minimum 5 seconds
        watch_time_int = int(watch_time)
        
        logger.info(f"Profile {profile_name}: watching {watch_percentage}% ({watch_time_int}s of {video_duration}s)")
        
        result_data["watch_percentage"] = watch_percentage
        result_data["watch_time_seconds"] = watch_time_int
        
        # Simulate video watching (the video is already open in the browser)
        await asyncio.sleep(watch_time)
        
        # ================== PERFORM ACTIONS BASED ON CAMPAIGN TYPE ==================
        
        # Handle LIKES - like the video if campaign type includes likes
        if request.campaign_type in ['likes', 'likes_comments']:
            logger.info(f"Profile {profile_name}: Performing LIKE action...")
            like_result = await YouTubeActions.like_video(profile_name, request.video_url)
            result_data["actions_performed"]["like"] = like_result
            
            if like_result.get("success"):
                # Report like to Laravel with metadata including watch data
                already_liked = like_result.get("already_liked", False)
                await YouTubeActions.report_action_to_laravel(
                    request.campaign_id, profile_name, "like",
                    metadata={
                        "already_liked": already_liked,
                        "watch_percentage": watch_percentage,
                        "watch_duration": watch_time_int
                    }
                )
                if already_liked:
                    logger.info(f"Profile {profile_name}: Video was already liked!")
                else:
                    logger.info(f"Profile {profile_name}: Like successful!")
            else:
                logger.warning(f"Profile {profile_name}: Like failed - {like_result.get('error')}")
        
        # Handle COMMENTS - post a random comment if campaign type includes comments
        if request.campaign_type in ['comments', 'likes_comments']:
            # Add small delay between like and comment
            if request.campaign_type == 'likes_comments':
                await asyncio.sleep(random.uniform(2, 5))
            
            logger.info(f"Profile {profile_name}: Performing COMMENT action...")
            comment_result = await YouTubeActions.post_comment(profile_name, request.video_url)
            result_data["actions_performed"]["comment"] = comment_result
            
            if comment_result.get("success"):
                # Report comment to Laravel with the comment text and watch data
                comment_text = comment_result.get("comment", "")
                await YouTubeActions.report_action_to_laravel(
                    request.campaign_id, profile_name, "comment",
                    metadata={
                        "comment_text": comment_text,
                        "watch_percentage": watch_percentage,
                        "watch_duration": watch_time_int
                    }
                )
                logger.info(f"Profile {profile_name}: Comment posted: {comment_text[:50]}...")
            else:
                logger.warning(f"Profile {profile_name}: Comment failed - {comment_result.get('error')}")
        
        # Handle VIEWS - report view to Laravel (for all campaign types that watch video)
        if request.campaign_type == 'views' or request.campaign_type in ['likes', 'comments', 'likes_comments']:
            view_result = await VideoWatcher.report_view_to_laravel(
                campaign_id=request.campaign_id,
                profile_name=profile_name,
                watch_percentage=watch_percentage,
                watch_duration_seconds=watch_time_int,
                video_duration_seconds=video_duration
            )
            result_data["view_reported"] = view_result.get("success", False)
        
        # Notify profile is ready for next campaign
        await VideoWatcher.notify_profile_ready(profile_name, request.campaign_id)
        
        result_data["success"] = True
        return result_data
    
    # === BATCHED EXECUTION ===
    from app.services.campaign_config import CampaignConfig
    
    # Determine batch size (from request or auto-detect)
    batch_size = CampaignConfig.get_batch_size(request.batch_size)
    batches = [profiles_to_process[i:i + batch_size] for i in range(0, len(profiles_to_process), batch_size)]
    total_batches = len(batches)
    
    logger.info(f"Processing {len(profiles_to_process)} profiles in {total_batches} batches (size: {batch_size})")
    
    all_results = []
    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} profiles)")
        
        # Mark profiles as running
        for p in batch:
            CampaignCache.mark_profile_running(request.campaign_id, p.get("profile_name"))
        
        # Process batch concurrently
        tasks = [watch_for_profile(p) for p in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results and update cache status
        for i, r in enumerate(batch_results):
            profile_name = batch[i].get("profile_name") if i < len(batch) else None
            if isinstance(r, Exception):
                all_results.append({"success": False, "error": str(r)})
                if profile_name:
                    CampaignCache.mark_profile_failed(request.campaign_id, profile_name, str(r))
            else:
                all_results.append(r)
                if profile_name and r.get("success"):
                    CampaignCache.mark_profile_completed(
                        request.campaign_id, 
                        profile_name,
                        r.get("actions_performed", {})
                    )
                elif profile_name:
                    CampaignCache.mark_profile_failed(request.campaign_id, profile_name, r.get("error", "Unknown error"))
        
        # Delay between batches (except for last batch)
        if batch_num < total_batches:
            logger.info(f"Waiting {CampaignConfig.BATCH_DELAY}s before next batch...")
            await asyncio.sleep(CampaignConfig.BATCH_DELAY)
    
    # Results are already processed during batching
    processed_results = all_results
    
    successful = sum(1 for r in processed_results if r.get("success", False))
    
    # Count action successes
    likes_success = sum(
        1 for r in processed_results 
        if r.get("actions_performed", {}).get("like", {}).get("success")
    )
    comments_success = sum(
        1 for r in processed_results 
        if r.get("actions_performed", {}).get("comment", {}).get("success")
    )
    
    return APIResponse(
        success=True,
        message=f"Completed campaign for {successful}/{len(processed_results)} profiles",
        data={
            "campaign_id": request.campaign_id,
            "campaign_type": request.campaign_type,
            "video_url": request.video_url,
            "video_duration": video_duration,
            "results": processed_results,
            "summary": {
                "total_profiles": len(processed_results),
                "successful": successful,
                "likes_success": likes_success,
                "comments_success": comments_success
            },
            "cache_status": CampaignCache.get_campaign_status(request.campaign_id)
        }
    )


@router.get("/campaign/{campaign_id}/status", response_model=APIResponse)
async def get_campaign_status(campaign_id: int):
    """Get the current execution status of a campaign from cache."""
    from app.services.campaign_cache import CampaignCache
    
    status = CampaignCache.get_campaign_status(campaign_id)
    
    if not status:
        return APIResponse(
            success=False,
            message=f"Campaign {campaign_id} not found in cache",
            data=None
        )
    
    return APIResponse(
        success=True,
        message=f"Campaign status retrieved",
        data=status
    )


@router.get("/campaigns/active", response_model=APIResponse)
async def get_active_campaigns():
    """Get all active campaigns in cache (for dashboard)."""
    from app.services.campaign_cache import CampaignCache
    
    campaigns = CampaignCache.get_all_campaigns()
    
    return APIResponse(
        success=True,
        message=f"Found {len(campaigns)} campaigns in cache",
        data={"campaigns": campaigns}
    )


@router.delete("/campaign/{campaign_id}/cache", response_model=APIResponse)
async def clear_campaign_cache(campaign_id: int):
    """Clear a campaign from cache (e.g., to force fresh start)."""
    from app.services.campaign_cache import CampaignCache
    
    success = CampaignCache.clear_campaign(campaign_id)
    
    return APIResponse(
        success=success,
        message=f"Campaign {campaign_id} {'cleared from cache' if success else 'not found in cache'}",
        data=None
    )


@router.post("/campaign/{campaign_id}/cancel", response_model=APIResponse)
async def cancel_campaign(campaign_id: int):
    """
    Cancel a running campaign and close all its browser profiles.
    This sets a flag that the running batches will check and stop.
    """
    from app.services.campaign_cache import CampaignCache
    
    # Mark campaign as cancelled
    cancelled = CampaignCache.cancel_campaign(campaign_id)
    
    if not cancelled:
        return APIResponse(
            success=False,
            message=f"Campaign {campaign_id} not found in cache",
            data=None
        )
    
    # Get running profiles and close their browsers
    running_profiles = CampaignCache.get_running_profiles(campaign_id)
    closed_count = 0
    errors = []
    
    for profile_name in running_profiles:
        try:
            close_result = BrowserService.close_browser(profile_name)
            if close_result.get("success"):
                closed_count += 1
                # Mark profile as failed (cancelled)
                CampaignCache.mark_profile_failed(campaign_id, profile_name, "Campaign cancelled")
            else:
                errors.append(f"{profile_name}: {close_result.get('error', 'Unknown')}")
        except Exception as e:
            errors.append(f"{profile_name}: {str(e)}")
    
    return APIResponse(
        success=True,
        message=f"Campaign {campaign_id} cancelled. Closed {closed_count}/{len(running_profiles)} browsers.",
        data={
            "campaign_id": campaign_id,
            "browsers_closed": closed_count,
            "running_profiles": len(running_profiles),
            "errors": errors
        }
    )


class SyncStatusRequest(BaseModel):
    """Request model for syncing campaign status from Laravel."""
    status: str = Field(..., description="Status: 'running', 'paused', 'cancelled', 'completed'")


@router.post("/campaign/{campaign_id}/sync-status", response_model=APIResponse)
async def sync_campaign_status(campaign_id: int, request: SyncStatusRequest):
    """
    Sync campaign status from Laravel to Python.
    Called when Laravel changes campaign status (pause, cancel, resume).
    """
    from app.services.campaign_cache import CampaignCache
    
    logger.info(f"Syncing campaign {campaign_id} status to: {request.status}")
    
    if request.status in ('paused', 'cancelled'):
        # Cancel local campaign - stop processing and close browsers
        CampaignCache.cancel_campaign(campaign_id)
        
        # Close running browsers
        running_profiles = CampaignCache.get_running_profiles(campaign_id)
        for profile_name in running_profiles:
            try:
                BrowserService.close_browser(profile_name)
                CampaignCache.mark_profile_failed(campaign_id, profile_name, f"Campaign {request.status}")
            except:
                pass
        
        return APIResponse(
            success=True,
            message=f"Campaign {campaign_id} synced to {request.status}",
            data={"campaign_id": campaign_id, "status": request.status, "browsers_stopped": len(running_profiles)}
        )
    
    elif request.status == 'running':
        # Restart campaign if it was cancelled
        CampaignCache.restart_campaign(campaign_id)
        return APIResponse(
            success=True,
            message=f"Campaign {campaign_id} synced to running (restarted)",
            data={"campaign_id": campaign_id, "status": request.status}
        )
    
    return APIResponse(
        success=True,
        message=f"Campaign {campaign_id} status noted: {request.status}",
        data={"campaign_id": campaign_id, "status": request.status}
    )

class CampaignActionRequest(BaseModel):
    """Request model for campaign actions (like, comment, or both)."""
    campaign_id: int = Field(..., description="Campaign ID")
    campaign_type: str = Field(..., description="Type: 'likes', 'comments', 'likes_comments'")
    profiles: List[dict] = Field(..., description="List of {profile_name}")
    video_url: str = Field(..., description="YouTube video URL")


@router.post("/campaign/action", response_model=APIResponse)
async def perform_campaign_action(request: CampaignActionRequest):
    """
    Perform campaign actions (like, comment, or both) on a YouTube video.
    
    Campaign types:
    - 'likes': Only like the video
    - 'comments': Only post a random comment
    - 'likes_comments': Like the video and post a random comment
    """
    from app.services.youtube_actions import YouTubeActions, perform_campaign_actions
    
    logger.info(f"Starting campaign action '{request.campaign_type}' for campaign {request.campaign_id}")
    logger.info(f"Video URL: {request.video_url}, Profiles: {len(request.profiles)}")
    
    # Validate campaign type
    valid_types = ['likes', 'comments', 'likes_comments', 'views']
    if request.campaign_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid campaign type. Must be one of: {valid_types}")
    
    # Perform actions for all profiles
    results = await perform_campaign_actions(
        campaign_id=request.campaign_id,
        campaign_type=request.campaign_type,
        profiles=request.profiles,
        video_url=request.video_url
    )
    
    # Count successes
    successful = sum(1 for r in results if r.get("success", False))
    
    # Build action summary
    action_summary = {
        "likes_success": 0,
        "comments_success": 0
    }
    for r in results:
        if r.get("actions", {}).get("like", {}).get("success"):
            action_summary["likes_success"] += 1
        if r.get("actions", {}).get("comment", {}).get("success"):
            action_summary["comments_success"] += 1
    
    return APIResponse(
        success=True,
        message=f"Completed {request.campaign_type} actions for {successful}/{len(results)} profiles",
        data={
            "campaign_id": request.campaign_id,
            "campaign_type": request.campaign_type,
            "video_url": request.video_url,
            "results": results,
            "summary": action_summary,
            "total_profiles": len(results)
        }
    )


@router.delete("/{profile_path:path}", response_model=APIResponse)
async def delete_profile(profile_path: str):
    """Delete a specific profile."""
    try:
        # First close browser if running
        profile_name = profile_path.split("/")[-1]
        BrowserService.close_browser(profile_name)
        
        success = profile_service.delete_profile(profile_path)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found or already deleted")
        
        return APIResponse(
            success=True,
            message="Profile deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Cookie Management Endpoints ==============

class CookieImportRequest(BaseModel):
    """Request model for importing cookies."""
    profile_path: str = Field(..., description="Path to profile directory")
    cookies: List[dict] = Field(..., description="Cookies in EditThisCookie JSON format")
    google_only: bool = Field(default=True, description="Only import Google/YouTube cookies")


class BulkCookieImportRequest(BaseModel):
    """Request model for bulk cookie import to multiple profiles."""
    profiles: List[str] = Field(..., description="List of profile paths")
    cookies: List[dict] = Field(..., description="Cookies in EditThisCookie JSON format")
    google_only: bool = Field(default=True, description="Only import Google/YouTube cookies")


@router.post("/cookies/import", response_model=APIResponse)
async def import_cookies(request: CookieImportRequest):
    """
    Import cookies into a Chrome profile for auto-login.
    
    Cookies should be in EditThisCookie/Cookie Editor export format:
    [
        {
            "name": "SID",
            "value": "xxx",
            "domain": ".google.com",
            "path": "/",
            "expirationDate": 1735689600,
            "secure": true,
            "httpOnly": true
        }
    ]
    """
    from app.services.cookie_manager import CookieManager
    
    logger.info(f"Importing cookies to profile: {request.profile_path}")
    
    if request.google_only:
        result = CookieManager.import_google_cookies(request.profile_path, request.cookies)
    else:
        result = CookieManager.import_cookies_to_profile(request.profile_path, request.cookies)
    
    if result.get("success"):
        return APIResponse(
            success=True,
            message=result.get("message", "Cookies imported"),
            data=result
        )
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to import cookies"))


@router.post("/cookies/import-bulk", response_model=APIResponse)
async def import_cookies_bulk(request: BulkCookieImportRequest):
    """
    Import the same cookies to multiple profiles.
    Useful for importing one Google account cookies to many profiles.
    """
    from app.services.cookie_manager import CookieManager
    
    logger.info(f"Bulk importing cookies to {len(request.profiles)} profiles")
    
    results = []
    for profile_path in request.profiles:
        if request.google_only:
            result = CookieManager.import_google_cookies(profile_path, request.cookies)
        else:
            result = CookieManager.import_cookies_to_profile(profile_path, request.cookies)
        
        results.append({
            "profile_path": profile_path,
            "success": result.get("success", False),
            "imported": result.get("imported", 0),
            "error": result.get("error")
        })
    
    successful = sum(1 for r in results if r["success"])
    
    return APIResponse(
        success=True,
        message=f"Imported cookies to {successful}/{len(results)} profiles",
        data={"results": results, "successful": successful}
    )


@router.get("/cookies/export", response_model=APIResponse)
async def export_cookies(
    profile_path: str = Query(..., description="Path to profile directory"),
    google_only: bool = Query(default=True, description="Only export Google/YouTube cookies")
):
    """
    Export cookies from a Chrome profile.
    Can be used to extract cookies from a logged-in profile.
    """
    from app.services.cookie_manager import CookieManager
    
    domains = [".google.com", ".youtube.com"] if google_only else None
    result = CookieManager.export_cookies_from_profile(profile_path, domains)
    
    if result.get("success"):
        return APIResponse(
            success=True,
            message=f"Exported {result.get('count', 0)} cookies",
            data=result
        )
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to export cookies"))


