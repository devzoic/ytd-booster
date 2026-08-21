"""
Batched campaign executor for optimized resource management.
Processes profiles in batches to prevent system overload.
"""

import asyncio
from typing import Dict, Any, List, Optional

from app.utils.logger import setup_logger
from app.services.campaign_config import CampaignConfig
from app.services.browser_service import BrowserService
from app.services.youtube_actions import YouTubeActions
from app.services.video_watcher import VideoWatcher

logger = setup_logger(__name__)


class CampaignExecutor:
    """
    Executes campaigns in optimized batches.
    
    Instead of opening all browser tabs simultaneously:
    1. Divides profiles into batches (e.g., 5 at a time)
    2. Processes each batch sequentially
    3. Manages tabs and resources efficiently
    """
    
    @classmethod
    async def execute_campaign(
        cls,
        campaign_id: int,
        profiles: List[Dict[str, Any]],
        video_url: str,
        campaign_type: str,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute campaign with intelligent batching.
        
        Args:
            campaign_id: Campaign ID
            profiles: List of profile dicts with profile_path, name, debug_port, etc.
            video_url: YouTube video URL
            campaign_type: 'views', 'likes', 'comments', 'likes_comments'
            batch_size: Optional batch size (auto-detect if None)
            
        Returns:
            Dict with execution results
        """
        # Determine batch size
        effective_batch_size = CampaignConfig.get_batch_size(batch_size)
        
        # Create batches
        batches = [profiles[i:i + effective_batch_size] for i in range(0, len(profiles), effective_batch_size)]
        total_batches = len(batches)
        
        logger.info(
            f"Campaign {campaign_id}: Executing with {len(profiles)} profiles in "
            f"{total_batches} batches (batch size: {effective_batch_size})"
        )
        
        all_results = []
        failed_count = 0
        success_count = 0
        
        for batch_num, batch in enumerate(batches, 1):
            logger.info(f"Campaign {campaign_id}: Processing batch {batch_num}/{total_batches} ({len(batch)} profiles)")
            
            # Process batch
            batch_results = await cls.process_batch(
                campaign_id=campaign_id,
                profiles=batch,
                video_url=video_url,
                campaign_type=campaign_type,
                batch_num=batch_num,
                total_batches=total_batches
            )
            
            all_results.extend(batch_results)
            
            # Count successes/failures
            for result in batch_results:
                if result.get("success"):
                    success_count += 1
                else:
                    failed_count += 1
            
            # Delay before next batch (except for last batch)
            if batch_num < total_batches:
                logger.info(f"Waiting {CampaignConfig.BATCH_DELAY}s before next batch...")
                await asyncio.sleep(CampaignConfig.BATCH_DELAY)
        
        logger.info(
            f"Campaign {campaign_id}: Completed - {success_count} success, {failed_count} failed"
        )
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "total_profiles": len(profiles),
            "total_batches": total_batches,
            "batch_size": effective_batch_size,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": all_results
        }
    
    @classmethod
    async def process_batch(
        cls,
        campaign_id: int,
        profiles: List[Dict[str, Any]],
        video_url: str,
        campaign_type: str,
        batch_num: int,
        total_batches: int
    ) -> List[Dict[str, Any]]:
        """
        Process a single batch of profiles.
        
        Flow:
        1. Open video tabs with staggered delay
        2. Wait for video watching (concurrent)
        3. Perform actions (like/comment) with staggered delay
        4. Close video tabs
        5. Report completion
        
        Args:
            Same as execute_campaign plus batch_num and total_batches
            
        Returns:
            List of results for each profile in the batch
        """
        results = []
        
        # Get video duration once for the batch
        video_duration = await VideoWatcher.get_video_duration(video_url)
        
        # 1. Open video tabs with staggered delay
        logger.info(f"Batch {batch_num}: Opening video tabs...")
        for profile in profiles:
            debug_port = profile.get("debug_port")
            profile_name = profile.get("name", "unknown")
            
            if debug_port:
                try:
                    await YouTubeActions.open_url_in_browser(debug_port, video_url)
                    logger.info(f"Opened video tab for {profile_name}")
                except Exception as e:
                    logger.warning(f"Failed to open tab for {profile_name}: {e}")
                
                # Stagger tab opens
                await asyncio.sleep(CampaignConfig.TAB_OPEN_DELAY)
        
        # 2. Calculate and wait for watch duration
        watch_percentage = VideoWatcher.get_random_watch_percentage()
        base_watch_time = int((video_duration * watch_percentage) / 100)
        # Minimum 5 seconds watch
        watch_time = max(5, base_watch_time)
        
        logger.info(
            f"Batch {batch_num}: Watching video for {watch_time}s "
            f"({watch_percentage}% of {video_duration}s)"
        )
        await asyncio.sleep(watch_time)
        
        # 3. Perform actions for each profile
        for profile in profiles:
            profile_name = profile.get("name", "unknown")
            debug_port = profile.get("debug_port")
            profile_result = {
                "profile_name": profile_name,
                "success": True,
                "actions_performed": {},
                "watch_percentage": watch_percentage,
                "watch_duration": watch_time
            }
            
            try:
                if debug_port:
                    # Handle LIKES
                    if campaign_type in ['likes', 'likes_comments']:
                        like_result = await YouTubeActions.like_video(profile_name, video_url)
                        profile_result["actions_performed"]["like"] = like_result
                        
                        if like_result.get("success"):
                            already_liked = like_result.get("already_liked", False)
                            await YouTubeActions.report_action_to_laravel(
                                campaign_id, profile_name, "like",
                                metadata={
                                    "already_liked": already_liked,
                                    "watch_percentage": watch_percentage,
                                    "watch_duration": watch_time
                                }
                            )
                        
                        await asyncio.sleep(CampaignConfig.ACTION_DELAY)
                    
                    # Handle COMMENTS
                    if campaign_type in ['comments', 'likes_comments']:
                        if campaign_type == 'likes_comments':
                            await asyncio.sleep(2)  # Delay between like and comment
                        
                        comment_result = await YouTubeActions.post_comment(profile_name, video_url)
                        profile_result["actions_performed"]["comment"] = comment_result
                        
                        if comment_result.get("success"):
                            comment_text = comment_result.get("comment", "")
                            await YouTubeActions.report_action_to_laravel(
                                campaign_id, profile_name, "comment",
                                metadata={
                                    "comment_text": comment_text,
                                    "watch_percentage": watch_percentage,
                                    "watch_duration": watch_time
                                }
                            )
                        
                        await asyncio.sleep(CampaignConfig.ACTION_DELAY)
                    
                    # Report VIEW
                    await VideoWatcher.report_view_to_laravel(
                        campaign_id=campaign_id,
                        profile_name=profile_name,
                        watch_percentage=watch_percentage,
                        watch_duration_seconds=watch_time,
                        video_duration_seconds=video_duration
                    )
                    
                    # 4. Close video tab
                    await cls.close_video_tab(debug_port)
                    
                    # Mark profile as ready
                    await VideoWatcher.notify_profile_ready(profile_name, campaign_id)
                
            except Exception as e:
                logger.error(f"Error processing profile {profile_name}: {e}")
                profile_result["success"] = False
                profile_result["error"] = str(e)
            
            results.append(profile_result)
        
        logger.info(f"Batch {batch_num}: Completed processing")
        return results
    
    @classmethod
    async def close_video_tab(cls, debug_port: int) -> bool:
        """
        Close the current video tab, keeping the browser open.
        
        Args:
            debug_port: Chrome DevTools Protocol port
            
        Returns:
            True if successful
        """
        try:
            js = """
            (async () => {
                // Navigate away instead of closing to keep browser alive
                window.location.href = 'about:blank';
                return { success: true };
            })();
            """
            result = await YouTubeActions.execute_js_in_browser(debug_port, js)
            return result.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to close tab on port {debug_port}: {e}")
            return False
