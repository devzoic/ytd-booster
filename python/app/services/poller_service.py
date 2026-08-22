"""
Background poller service for pulling and executing campaign jobs from Laravel.
"""

import asyncio
import random
import httpx
from app.config import settings
from app.services.browser_service import BrowserService
from app.services.video_watcher import VideoWatcher
from app.services.youtube_actions import YouTubeActions
from app.services.campaign_config import CampaignConfig
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PollerService:
    """Manages periodic polling of Laravel queue and concurrent job execution."""

    def __init__(self):
        self.active_tasks = set()
        self.launch_lock = asyncio.Lock()
        self.running = False

    async def start(self):
        """Start the poller background loop."""
        if self.running:
            return
        
        self.running = True
        logger.info("Poller service started successfully")
        
        while self.running:
            try:
                # 1. Determine optimal concurrency limit based on RAM
                max_concurrency = CampaignConfig.get_optimal_batch_size()
                active_workers = len(self.active_tasks)
                available_workers = max_concurrency - active_workers
                
                if available_workers > 0:
                    if settings.SAAS_DEVICE_KEY:
                        await self._poll_jobs(available_workers)
                    else:
                        logger.warning("SAAS_DEVICE_KEY is not configured in settings. Poller is waiting.")
                    
            except Exception as e:
                logger.error(f"Error in poller loop: {e}")
                
            # Wait before next poll tick
            await asyncio.sleep(12)

    async def stop(self):
        """Stop the poller background loop."""
        self.running = False
        logger.info("Stopping poller service...")

    async def _poll_jobs(self, available_workers: int):
        """Poll the Laravel server for eligible jobs."""
        import socket
        clean_hostname = socket.gethostname().split(".")[0]

        url = f"{settings.LARAVEL_API_URL.rstrip('/')}/device/poll"
        payload = {
            "device_key": settings.SAAS_DEVICE_KEY,
            "device_name": clean_hostname,
            "api_url": "",
            "available_workers": available_workers
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        jobs = data.get("jobs", [])
                        if jobs:
                            logger.info(f"Pulled {len(jobs)} new campaign jobs from Laravel")
                            for job in jobs:
                                task = asyncio.create_task(self._execute_job(job))
                                self.active_tasks.add(task)
                                task.add_done_callback(self.active_tasks.discard)
                        else:
                            logger.info("Polled Laravel queue: 0 jobs currently eligible")
                    else:
                        logger.warning(f"Laravel poll returned success=false: {data.get('message', 'No message')}")
                elif response.status_code == 401:
                    logger.warning("Device key authorization failed (401). Please check SAAS_DEVICE_KEY.")
                else:
                    logger.warning(f"Laravel poll returned unexpected status {response.status_code}: {response.text}")
            except Exception as e:
                logger.warning(f"Failed to connect to Laravel for polling at {url}: {e}")

    async def _execute_job(self, job: dict):
        """Execute a single pulled job."""
        job_id = job.get("job_id")
        campaign_id = job.get("campaign_id")
        video_url = job.get("video_url")
        campaign_type = job.get("campaign_type")
        activity_type = job.get("activity_type")
        subscribe = job.get("subscribe", False)
        profile_name = job.get("profile_name")
        profile_path = job.get("profile_path")
        proxy = job.get("proxy")
        google_cookies = job.get("google_cookies")
        
        logger.info(f"Starting job {job_id} for profile {profile_name} (Type: {activity_type}, Subscribe: {subscribe})")
        
        result_data = {
            "job_id": job_id,
            "status": "failed",
            "watch_percentage": 0,
            "watch_duration_seconds": 0,
            "comment_text": None,
            "error_message": None
        }
        
        try:
            # 1. Force close any lingering browser processes
            try:
                BrowserService.close_browser(profile_name)
            except:
                pass
            
            # 2. Fetch video metadata once
            metadata = await VideoWatcher.get_video_metadata(video_url)
            video_duration = metadata.get("duration", 180)
            video_title = metadata.get("title", "YouTube Video")
            video_uploader = metadata.get("uploader", "")
            
            # 3. Roll random execution mode: 20% Direct Link, 40% Search, 40% Warmup + Search
            roll = random.random()
            if roll < 0.2:
                mode = "direct"
            elif roll < 0.6:
                mode = "search"
            else:
                mode = "warmup_search"
                
            logger.info(f"Execution mode chosen: '{mode.upper()}' for profile {profile_name}")
            
            # Format direct video URL with autoplay parameter
            formatted_url = video_url
            if 'youtube.com' in formatted_url or 'youtu.be' in formatted_url:
                if '?' in formatted_url:
                    formatted_url += '&autoplay=1&mute=0'
                else:
                    formatted_url += '?autoplay=1&mute=0'
            
            launch_url = formatted_url if mode == "direct" else "https://www.youtube.com"

            # 4. Acquire lock to stagger browser startups (prevent CPU surges)
            async with self.launch_lock:
                stagger_delay = random.uniform(5.0, 15.0)
                logger.info(f"Staggering launch for {profile_name}: waiting {stagger_delay:.1f}s...")
                await asyncio.sleep(stagger_delay)
                
                logger.info(f"Launching browser for profile {profile_name} on {launch_url}")
                launch_result = BrowserService.launch_browser(profile_path, launch_url, proxy)
            
            if not launch_result.get("success"):
                result_data["error_message"] = f"Failed to launch: {launch_result.get('error', 'Unknown')}"
                await self._report_job(result_data)
                return
            
            debug_port = launch_result.get("debug_port")
            
            # 5. Inject Google cookies
            if debug_port and google_cookies:
                try:
                    from app.services.cookie_manager import CookieManager
                    await CookieManager.inject_cookies_via_cdp(
                        debug_port, 
                        google_cookies, 
                        domains=[".google.com", ".youtube.com"]
                    )
                except Exception as ce:
                    logger.warning(f"Failed to inject Google cookies for {profile_name}: {ce}")
            
            # 6. Human-like interactions & Warmups
            if debug_port:
                try:
                    from app.services.browser_interaction import BrowserInteraction
                    await asyncio.sleep(2)
                    await BrowserInteraction.inject_stealth_patches(debug_port)
                    await asyncio.sleep(2)
                    
                    # Detect bot check
                    bot_check = await BrowserInteraction.detect_bot_check(debug_port)
                    if bot_check.get("detected", False):
                        phrase = bot_check.get("phrase", "unknown")
                        logger.warning(f"⚠️ {profile_name}: Bot detection triggered! ({phrase})")
                        result_data["error_message"] = f"Bot check: {phrase}"
                        BrowserService.close_browser(profile_name)
                        await self._report_job(result_data)
                        return
                    
                    # Mode execution
                    if mode == "warmup_search":
                        # Browse a random recommended homepage video first
                        await BrowserInteraction.simulate_homepage_warmup(debug_port)
                        await asyncio.sleep(2)
                        
                        # Verify bot check
                        bot_check = await BrowserInteraction.detect_bot_check(debug_port)
                        if bot_check.get("detected", False):
                            phrase = bot_check.get("phrase", "unknown")
                            logger.warning(f"⚠️ {profile_name}: Bot detection triggered after warmup! ({phrase})")
                            result_data["error_message"] = f"Bot check post-warmup: {phrase}"
                            BrowserService.close_browser(profile_name)
                            await self._report_job(result_data)
                            return
                    
                    if mode in ("search", "warmup_search"):
                        # Search for the video and click it
                        # Keywords: fuzzy combination of title + channel name to look organic
                        search_keywords = video_title[:50]
                        if random.random() < 0.6 and video_uploader:
                            search_keywords = f"{video_uploader} {search_keywords}"
                            
                        search_success = await BrowserInteraction.search_and_click_video(
                            debug_port, 
                            search_keywords, 
                            video_uploader, 
                            video_title
                        )
                        
                        if not search_success:
                            # Search-to-click failed (e.g. video not found on search results)
                            # Fallback to direct navigation as safety net so job doesn't fail!
                            logger.warning(f"Search-to-click failed for {profile_name}. Falling back to direct navigation...")
                            async with self.launch_lock:
                                await BrowserInteraction.inject_stealth_patches(debug_port)
                                # Load target directly using CDP
                                import websockets, json as json_module
                                targets_res = await httpx.AsyncClient().get(f"http://127.0.0.1:{debug_port}/json")
                                page_target = next((t for t in targets_res.json() if t.get("type") == "page"), None)
                                if page_target:
                                    ws_url = page_target.get("webSocketDebuggerUrl")
                                    if ws_url and "localhost" in ws_url:
                                        ws_url = ws_url.replace("localhost", "127.0.0.1")
                                    if ws_url:
                                        async with websockets.connect(ws_url) as ws:
                                            await ws.send(json_module.dumps({"id": 99, "method": "Page.navigate", "params": {"url": formatted_url}}))
                            await asyncio.sleep(4)
                    
                    await BrowserInteraction.ensure_video_playing(debug_port)
                    
                    # Handle ads
                    await BrowserInteraction.handle_youtube_ads(debug_port, max_wait_seconds=15)
                    await BrowserInteraction.ensure_video_playing(debug_port)
                except Exception as ie:
                    logger.warning(f"Interaction setups failed for {profile_name}: {ie}")
            
            # 7. Watch duration setup
            watch_percentage = VideoWatcher.get_random_watch_percentage()
            watch_time = max(5, (video_duration * watch_percentage) / 100 + random.uniform(-2, 2))
            
            logger.info(f"Watching {watch_percentage}% ({int(watch_time)}s of {video_duration}s)")
            
            # 6. Watch video loop
            elapsed = 0
            while elapsed < watch_time:
                # Periodic bot check
                if debug_port and elapsed > 0 and elapsed % 5 < 1:
                    try:
                        from app.services.browser_interaction import BrowserInteraction
                        bot_check = await BrowserInteraction.detect_bot_check(debug_port)
                        if bot_check.get("detected", False):
                            phrase = bot_check.get("phrase", "unknown")
                            result_data["error_message"] = f"Bot check during playback: {phrase}"
                            BrowserService.close_browser(profile_name)
                            await self._report_job(result_data)
                            return
                    except:
                        pass
                
                # Mouse movements
                if debug_port and elapsed > 0 and elapsed % 10 < 1:
                    try:
                        from app.services.browser_interaction import BrowserInteraction
                        await BrowserInteraction.simulate_human_presence(debug_port, duration_seconds=1, interaction_count=1)
                    except:
                        pass
                
                await asyncio.sleep(min(1, watch_time - elapsed))
                elapsed += 1
            
            # 7. Perform actions
            comment_text = None
            
            # Perform Like
            if activity_type == 'like' or campaign_type == 'likes_comments':
                try:
                    like_res = await YouTubeActions.like_video(profile_name, video_url)
                    if not like_res.get("success"):
                        raise Exception(f"Like failed: {like_res.get('error', 'Unknown error')}")
                except Exception as le:
                    logger.error(f"Failed to post like: {le}")
                    raise le
            
            # Perform Comment
            if activity_type == 'comment' or campaign_type == 'likes_comments':
                try:
                    comment_result = await YouTubeActions.post_comment(profile_name, video_url)
                    if not comment_result.get("success"):
                        raise Exception(f"Comment failed: {comment_result.get('error', 'Unknown error')}")
                    comment_text = comment_result.get("comment")
                except Exception as ce:
                    logger.error(f"Failed to post comment: {ce}")
                    raise ce

            # Perform Subscribe (if enabled)
            if subscribe:
                try:
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                    sub_res = await YouTubeActions.subscribe_channel(profile_name, video_url)
                    if sub_res.get("success"):
                        await YouTubeActions.report_subscription_to_laravel(
                            campaign_id=campaign_id,
                            profile_name=profile_name,
                            status="subscribed"
                        )
                    else:
                        error_msg = sub_res.get("error", "Subscription failed")
                        logger.warning(f"Subscription failed for profile {profile_name}: {error_msg}")
                        await YouTubeActions.report_subscription_to_laravel(
                            campaign_id=campaign_id,
                            profile_name=profile_name,
                            status="failed",
                            error_message=error_msg
                        )
                except Exception as se:
                    logger.error(f"Failed to subscribe: {se}")
                    await YouTubeActions.report_subscription_to_laravel(
                        campaign_id=campaign_id,
                        profile_name=profile_name,
                        status="failed",
                        error_message=str(se)
                    )
            
            # Close browser
            BrowserService.close_browser(profile_name)
            
            # Populate success report
            result_data["status"] = "completed"
            result_data["watch_percentage"] = int(watch_percentage)
            result_data["watch_duration_seconds"] = int(watch_time)
            result_data["comment_text"] = comment_text
            
            await self._report_job(result_data)
            
        except Exception as e:
            logger.error(f"Exception executing job {job_id}: {e}")
            result_data["error_message"] = str(e)
            try:
                BrowserService.close_browser(profile_name)
            except:
                pass
            await self._report_job(result_data)

    async def _report_job(self, result_data: dict):
        """Report execution result back to Laravel."""
        url = f"{settings.LARAVEL_API_URL.rstrip('/')}/device/job-report"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=result_data, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Successfully reported job {result_data['job_id']} status ({result_data['status']}) to Laravel")
                else:
                    logger.error(f"Failed to report job status to Laravel: {response.text}")
            except Exception as e:
                logger.error(f"Exception reporting job status to Laravel: {e}")


# Global poller instance
poller_service = PollerService()
