"""
Video watcher service for YouTube video automation.
Plays videos for random duration based on REAL video duration and reports completion to Laravel.
"""

import asyncio
import random
import subprocess
import json
import re
import httpx
import sys
import platform
from pathlib import Path
from typing import Dict, Any, Optional

from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

def get_laravel_endpoint(endpoint: str) -> str:
    """Construct full Laravel API endpoint URL from settings."""
    base = (settings.LARAVEL_API_URL or "http://youtube.test/api").rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    clean_ep = endpoint.lstrip("/").replace("api/", "")
    return f"{base}/{clean_ep}"


class VideoWatcher:
    """Service for watching YouTube videos and reporting completion."""
    
    # Random watch percentage range (20-30%)
    MIN_WATCH_PERCENTAGE = 72
    MAX_WATCH_PERCENTAGE = 100
    
    # Cache video durations to avoid repeated lookups
    _duration_cache: Dict[str, int] = {}
    _metadata_cache: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    async def get_video_metadata(cls, video_url: str) -> Dict[str, Any]:
        """
        Get video metadata (duration, title, channel/uploader) from YouTube using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Dict containing: duration (int), title (str), uploader (str)
        """
        video_id = cls.extract_video_id(video_url)
        
        # Check cache first
        if video_id and video_id in cls._metadata_cache:
            return cls._metadata_cache[video_id]
        
        default_metadata = {
            "duration": 180,
            "title": "YouTube Video",
            "uploader": "",
            "thumbnail": "",
            "view_count": 0,
            "like_count": 0
        }
        
        max_retries = 3
        retry_delay = 2.0
        
        # Resolve yt-dlp path robustly (especially for virtualenvs on Windows)
        executable_dir = Path(sys.executable).parent
        is_windows = platform.system() == "Windows"
        ytdlp_filename = "yt-dlp.exe" if is_windows else "yt-dlp"
        ytdlp_path = executable_dir / ytdlp_filename
        
        if ytdlp_path.exists():
            ytdlp_cmd = str(ytdlp_path)
        else:
            ytdlp_cmd = "yt-dlp" # Fallback to path lookup
            
        for attempt in range(max_retries):
            try:
                # Use yt-dlp to get video info (fast, no download)
                result = await asyncio.to_thread(
                    subprocess.run,
                    [
                        ytdlp_cmd,
                        '--dump-json',
                        '--no-download',
                        '--no-warnings',
                        video_url
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=is_windows
                )
                
                if result.returncode == 0 and result.stdout:
                    info = json.loads(result.stdout)
                    duration = int(info.get('duration', 180))
                    title = info.get('title', 'YouTube Video')
                    uploader = info.get('uploader', '')
                    thumbnail = info.get('thumbnail', '')
                    view_count = int(info.get('view_count', 0))
                    like_count = int(info.get('like_count', 0))
                    
                    metadata = {
                        "duration": duration,
                        "title": title,
                        "uploader": uploader,
                        "thumbnail": thumbnail,
                        "view_count": view_count,
                        "like_count": like_count
                    }
                    
                    # Cache both metadata and duration for compatibility
                    if video_id:
                        cls._metadata_cache[video_id] = metadata
                        cls._duration_cache[video_id] = duration
                    
                    logger.info(f"Video metadata fetched: '{title}' by '{uploader}' ({duration}s, {view_count} views, {like_count} likes)")
                    return metadata
                else:
                    stderr_msg = result.stderr.strip() if result.stderr else "No stderr"
                    logger.warning(f"yt-dlp returned non-zero code {result.returncode} (Attempt {attempt+1}/{max_retries}). Error: {stderr_msg}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout getting video metadata for {video_url} (Attempt {attempt+1}/{max_retries})")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse video info json for {video_url} (Attempt {attempt+1}/{max_retries})")
            except Exception as e:
                logger.error(f"Error getting video metadata: {e} (Attempt {attempt+1}/{max_retries})")
                
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                
        return default_metadata

    @classmethod
    def get_random_watch_percentage(cls) -> int:
        """Get a random watch percentage between MIN and MAX."""
        return random.randint(cls.MIN_WATCH_PERCENTAGE, cls.MAX_WATCH_PERCENTAGE)
    
    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    async def get_video_duration(cls, video_url: str) -> int:
        """
        Get video duration in seconds from YouTube using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Duration in seconds, defaults to 180 if unable to fetch
        """
        video_id = cls.extract_video_id(video_url)
        
        # Check cache first
        if video_id and video_id in cls._duration_cache:
            return cls._duration_cache[video_id]
            
        metadata = await cls.get_video_metadata(video_url)
        return metadata.get("duration", 180)
    
    @classmethod
    async def report_view_to_laravel(
        cls, 
        campaign_id: int, 
        profile_name: str, 
        watch_percentage: int,
        watch_duration_seconds: int = 0,
        video_duration_seconds: int = 0
    ) -> Dict[str, Any]:
        """
        Send webhook to Laravel to record a view.
        
        Args:
            campaign_id: Campaign ID
            profile_name: Profile name that watched the video
            watch_percentage: Percentage of video watched
            watch_duration_seconds: Actual watch duration in seconds
            video_duration_seconds: Total video duration in seconds
            
        Returns:
            Response from Laravel API
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Retry up to 3 times for transient failures
                for attempt in range(3):
                    try:
                        response = await client.post(
                            get_laravel_endpoint("campaigns/record-view"),
                            json={
                                "campaign_id": campaign_id,
                                "profile_name": profile_name,
                                "watch_percentage": watch_percentage,
                                "watch_duration_seconds": watch_duration_seconds,
                                "video_duration_seconds": video_duration_seconds,
                            },
                            timeout=30
                        )
                        result = response.json()
                        logger.info(f"View reported for campaign {campaign_id}: {result}")
                        return result
                    except httpx.ConnectError as ce:
                        if attempt < 2:
                            logger.warning(f"Connection error (attempt {attempt + 1}), retrying...")
                            await asyncio.sleep(1)
                        else:
                            raise ce
        except Exception as e:
            logger.error(f"Failed to report view: {type(e).__name__}: {e}")
            return {"success": False, "message": str(e)}
    
    @classmethod
    async def notify_profile_ready(cls, profile_name: str, campaign_id: int = None) -> Dict[str, Any]:
        """
        Notify Laravel that profile is ready for next job.
        
        Args:
            profile_name: Profile name
            campaign_id: Optional campaign ID
            
        Returns:
            Response from Laravel API
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for attempt in range(3):
                    try:
                        response = await client.post(
                            get_laravel_endpoint("campaigns/profile-ready"),
                            json={
                                "profile_name": profile_name,
                                "campaign_id": campaign_id,
                            },
                            timeout=30
                        )
                        result = response.json()
                        logger.info(f"Profile {profile_name} marked as ready: {result}")
                        return result
                    except httpx.ConnectError as ce:
                        if attempt < 2:
                            logger.warning(f"Connection error notifying profile ready (attempt {attempt + 1}), retrying...")
                            await asyncio.sleep(1)
                        else:
                            raise ce
        except Exception as e:
            logger.error(f"Failed to notify profile ready: {type(e).__name__}: {e}")
            return {"success": False, "message": str(e)}
    
    @classmethod
    async def notify_bot_detection(cls, profile_name: str, campaign_id: int = None, reason: str = None) -> Dict[str, Any]:
        """
        Notify Laravel that a profile triggered bot detection.
        
        Args:
            profile_name: Profile name that was detected as bot
            campaign_id: Optional campaign ID
            reason: Bot detection reason/phrase
            
        Returns:
            Response from Laravel API
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    get_laravel_endpoint("campaigns/profile-bot-detected"),
                    json={
                        "profile_name": profile_name,
                        "campaign_id": campaign_id,
                        "reason": reason,
                    },
                    timeout=30
                )
                result = response.json()
                logger.info(f"Laravel notified of bot detection on {profile_name}: {result}")
                return result
        except Exception as e:
            logger.warning(f"Failed to notify Laravel of bot detection: {type(e).__name__}: {e}")
            return {"success": False, "message": str(e)}
    
    @classmethod
    async def watch_video(
        cls,
        campaign_id: int,
        profile_name: str,
        video_url: str
    ) -> Dict[str, Any]:
        """
        Watch a YouTube video for a random percentage of its duration.
        Fetches real video duration from YouTube.
        
        Args:
            campaign_id: Campaign ID
            profile_name: Profile name
            video_url: YouTube video URL
            
        Returns:
            Dict with watch result
        """
        try:
            # Get real video duration from YouTube
            video_duration = await cls.get_video_duration(video_url)
            
            # Calculate random watch time
            watch_percentage = cls.get_random_watch_percentage()
            watch_time = int((video_duration * watch_percentage) / 100)
            
            # Add some randomness to watch time (+/- 10 seconds)
            watch_time += random.randint(-10, 10)
            watch_time = max(30, watch_time)  # Minimum 30 seconds
            
            logger.info(
                f"Profile {profile_name} watching video for {watch_time}s "
                f"({watch_percentage}% of {video_duration}s)"
            )
            
            # Wait for the watch duration
            await asyncio.sleep(watch_time)
            
            # Report view to Laravel
            result = await cls.report_view_to_laravel(
                campaign_id=campaign_id,
                profile_name=profile_name,
                watch_percentage=watch_percentage,
                watch_duration_seconds=watch_time,
                video_duration_seconds=video_duration
            )
            
            # Notify profile is ready for next campaign
            await cls.notify_profile_ready(profile_name, campaign_id)
            
            return {
                "success": True,
                "profile_name": profile_name,
                "video_url": video_url,
                "video_duration": video_duration,
                "watch_percentage": watch_percentage,
                "watch_time_seconds": watch_time,
                "laravel_response": result
            }
            
        except Exception as e:
            logger.error(f"Error watching video for {profile_name}: {e}")
            return {"success": False, "profile_name": profile_name, "error": str(e)}
    
    @classmethod
    async def close_video_tab(cls, driver, video_url: str) -> bool:
        """
        Close only the tab with the video, not the entire browser.
        
        Args:
            driver: Selenium WebDriver
            video_url: URL of the tab to close
            
        Returns:
            True if tab closed successfully
        """
        try:
            current_handles = driver.window_handles
            
            if len(current_handles) <= 1:
                # Only one tab, don't close it - navigate to blank instead
                driver.get("about:blank")
                logger.info(f"Navigated to blank (only tab)")
                return True
            
            # Find and close the tab with the video
            for handle in current_handles:
                driver.switch_to.window(handle)
                if video_url in driver.current_url or 'youtube.com' in driver.current_url:
                    driver.close()
                    # Switch to remaining tab
                    driver.switch_to.window(driver.window_handles[0])
                    logger.info(f"Closed video tab, remaining tabs: {len(driver.window_handles)}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error closing video tab: {e}")
            return False


async def watch_videos_for_campaign(
    campaign_id: int,
    profiles: list[Dict[str, Any]],
    video_url: str
) -> list[Dict[str, Any]]:
    """
    Watch a video for multiple profiles concurrently.
    Each profile watches the video for a random percentage of its duration.
    
    Args:
        campaign_id: Campaign ID
        profiles: List of profile dicts with 'name' key
        video_url: YouTube video URL to watch
        
    Returns:
        List of results for each profile
    """
    # Pre-fetch video duration (shared across all profiles)
    video_duration = await VideoWatcher.get_video_duration(video_url)
    logger.info(f"Campaign {campaign_id}: Video duration is {video_duration}s")
    
    # Watch video for each profile
    tasks = [
        VideoWatcher.watch_video(
            campaign_id=campaign_id,
            profile_name=p.get("name", f"profile_{i}"),
            video_url=video_url
        )
        for i, p in enumerate(profiles)
    ]
    
    results = await asyncio.gather(*tasks)
    return list(results)


# Legacy function for backward compatibility
async def watch_video_simple(
    campaign_id: int,
    profile_name: str,
    video_url: str = None,
    video_duration_seconds: int = 180
) -> Dict[str, Any]:
    """
    Legacy simple video watch - now uses real duration if video_url provided.
    """
    if video_url:
        return await VideoWatcher.watch_video(
            campaign_id=campaign_id,
            profile_name=profile_name,
            video_url=video_url
        )
    
    # Fallback to old behavior if no URL provided
    watch_percentage = VideoWatcher.get_random_watch_percentage()
    watch_time = int((video_duration_seconds * watch_percentage) / 100)
    
    logger.info(f"Profile {profile_name} will watch for {watch_time}s ({watch_percentage}%)")
    
    await asyncio.sleep(watch_time)
    
    result = await VideoWatcher.report_view_to_laravel(
        campaign_id, 
        profile_name, 
        watch_percentage,
        watch_time,
        video_duration_seconds
    )
    
    return {
        "success": True,
        "profile_name": profile_name,
        "watch_percentage": watch_percentage,
        "watch_time_seconds": watch_time,
        "laravel_response": result
    }
