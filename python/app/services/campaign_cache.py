"""
Campaign cache for tracking profile completion state.
Prevents duplicate processing when campaigns are restarted.
Persists to file to survive server restarts.
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Cache file path
CACHE_FILE = Path(__file__).parent.parent.parent / "cache" / "campaigns.json"


@dataclass
class ProfileState:
    """State of a profile within a campaign."""
    status: str  # 'pending', 'running', 'completed', 'failed'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    actions_performed: Dict[str, bool] = field(default_factory=dict)
    
    def is_done(self) -> bool:
        """Check if profile has completed or failed."""
        return self.status in ('completed', 'failed')
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "actions_performed": self.actions_performed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProfileState":
        """Create from dict."""
        return cls(
            status=data.get("status", "pending"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            actions_performed=data.get("actions_performed", {})
        )


@dataclass
class CampaignState:
    """State of a campaign."""
    campaign_id: int
    video_url: str
    campaign_type: str
    batch_size: Optional[int]
    profiles: Dict[str, ProfileState] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    cancelled: bool = False  # Flag to signal campaign cancellation
    
    @property
    def total_profiles(self) -> int:
        return len(self.profiles)
    
    @property
    def completed_profiles(self) -> int:
        return sum(1 for p in self.profiles.values() if p.status == 'completed')
    
    @property
    def pending_profiles(self) -> int:
        return sum(1 for p in self.profiles.values() if p.status == 'pending')
    
    @property
    def running_profiles(self) -> int:
        return sum(1 for p in self.profiles.values() if p.status == 'running')
    
    @property
    def failed_profiles(self) -> int:
        return sum(1 for p in self.profiles.values() if p.status == 'failed')
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "campaign_id": self.campaign_id,
            "video_url": self.video_url,
            "campaign_type": self.campaign_type,
            "batch_size": self.batch_size,
            "profiles": {k: v.to_dict() for k, v in self.profiles.items()},
            "created_at": self.created_at.isoformat(),
            "cancelled": self.cancelled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CampaignState":
        """Create from dict."""
        profiles = {k: ProfileState.from_dict(v) for k, v in data.get("profiles", {}).items()}
        return cls(
            campaign_id=data["campaign_id"],
            video_url=data.get("video_url", ""),
            campaign_type=data.get("campaign_type", "views"),
            batch_size=data.get("batch_size"),
            profiles=profiles,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            cancelled=data.get("cancelled", False)
        )


class CampaignCache:
    """
    Cache for campaign execution state with file persistence.
    Tracks which profiles have completed actions to prevent duplicates on restart.
    """
    
    # Campaign storage: {campaign_id: CampaignState}
    _campaigns: Dict[int, CampaignState] = {}
    _loaded: bool = False  # Track if we've loaded from file
    
    @classmethod
    def save_to_file(cls) -> bool:
        """Save campaign cache to JSON file."""
        try:
            # Ensure cache directory exists
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            data = {
                str(cid): state.to_dict() 
                for cid, state in cls._campaigns.items()
            }
            
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(cls._campaigns)} campaigns to {CACHE_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to save campaign cache: {e}")
            return False
    
    @classmethod
    def load_from_file(cls) -> bool:
        """Load campaign cache from JSON file."""
        try:
            if not CACHE_FILE.exists():
                logger.debug("No cache file found, starting fresh")
                return False
            
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            
            # Reconstruct campaign states
            cls._campaigns = {
                int(cid): CampaignState.from_dict(state_data)
                for cid, state_data in data.items()
            }
            
            logger.info(f"Loaded {len(cls._campaigns)} campaigns from cache file")
            return True
        except Exception as e:
            logger.error(f"Failed to load campaign cache: {e}")
            return False
    
    @classmethod
    def _ensure_loaded(cls):
        """Ensure campaigns are loaded from file (once per server startup)."""
        if not cls._loaded:
            cls.load_from_file()
            cls._loaded = True
    
    @classmethod
    def register_campaign(
        cls,
        campaign_id: int,
        profile_names: list,
        video_url: str,
        campaign_type: str,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Register a campaign with its profiles.
        If campaign already exists, returns existing state and skips completed profiles.
        
        Args:
            campaign_id: Campaign ID
            profile_names: List of profile names to process
            video_url: Video URL
            campaign_type: Type of campaign
            batch_size: Optional batch size
            
        Returns:
            Dict with status and pending profiles
        """
        # Load from file if not yet loaded
        cls._ensure_loaded()
        
        if campaign_id in cls._campaigns:
            # Campaign already registered - check for resumption
            existing = cls._campaigns[campaign_id]
            pending = [name for name, state in existing.profiles.items() if not state.is_done()]
            completed = [name for name, state in existing.profiles.items() if state.status == 'completed']
            
            logger.info(
                f"Campaign {campaign_id} already registered: "
                f"{len(completed)} completed, {len(pending)} pending"
            )
            
            return {
                "status": "resumed",
                "message": f"Campaign resumed. {len(completed)} already completed, {len(pending)} pending.",
                "pending_profiles": pending,
                "completed_profiles": completed,
                "total_profiles": len(existing.profiles),
            }
        
        # Create new campaign state
        campaign_state = CampaignState(
            campaign_id=campaign_id,
            video_url=video_url,
            campaign_type=campaign_type,
            batch_size=batch_size,
        )
        
        # Initialize all profiles as pending
        for name in profile_names:
            campaign_state.profiles[name] = ProfileState(status='pending')
        
        cls._campaigns[campaign_id] = campaign_state
        
        # Save to file
        cls.save_to_file()
        
        logger.info(f"Campaign {campaign_id} registered with {len(profile_names)} profiles")
        
        return {
            "status": "new",
            "message": f"Campaign registered with {len(profile_names)} profiles",
            "pending_profiles": profile_names,
            "completed_profiles": [],
            "total_profiles": len(profile_names),
        }
    
    @classmethod
    def is_profile_completed(cls, campaign_id: int, profile_name: str) -> bool:
        """Check if a profile has already completed for this campaign."""
        campaign = cls._campaigns.get(campaign_id)
        if not campaign:
            return False
        
        profile_state = campaign.profiles.get(profile_name)
        if not profile_state:
            return False
        
        return profile_state.status == 'completed'
    
    @classmethod
    def mark_profile_running(cls, campaign_id: int, profile_name: str) -> None:
        """Mark a profile as currently running."""
        campaign = cls._campaigns.get(campaign_id)
        if campaign and profile_name in campaign.profiles:
            campaign.profiles[profile_name].status = 'running'
            campaign.profiles[profile_name].started_at = datetime.now()
            logger.debug(f"Profile {profile_name} marked as running for campaign {campaign_id}")
    
    @classmethod
    def mark_profile_completed(
        cls,
        campaign_id: int,
        profile_name: str,
        actions_performed: Optional[Dict[str, bool]] = None
    ) -> None:
        """Mark a profile as completed."""
        campaign = cls._campaigns.get(campaign_id)
        if campaign and profile_name in campaign.profiles:
            profile = campaign.profiles[profile_name]
            profile.status = 'completed'
            profile.completed_at = datetime.now()
            if actions_performed:
                profile.actions_performed = actions_performed
            
            # Save to file
            cls.save_to_file()
            
            logger.info(
                f"Profile {profile_name} completed for campaign {campaign_id} "
                f"({campaign.completed_profiles}/{campaign.total_profiles})"
            )
    
    @classmethod
    def mark_profile_failed(cls, campaign_id: int, profile_name: str, error: str) -> None:
        """Mark a profile as failed."""
        campaign = cls._campaigns.get(campaign_id)
        if campaign and profile_name in campaign.profiles:
            profile = campaign.profiles[profile_name]
            profile.status = 'failed'
            profile.completed_at = datetime.now()
            profile.error = error
            
            # Save to file
            cls.save_to_file()
            
            logger.warning(f"Profile {profile_name} failed for campaign {campaign_id}: {error}")
    
    @classmethod
    def get_pending_profiles(cls, campaign_id: int) -> list:
        """Get list of profiles that haven't completed yet."""
        campaign = cls._campaigns.get(campaign_id)
        if not campaign:
            return []
        
        return [name for name, state in campaign.profiles.items() if not state.is_done()]
    
    @classmethod
    def get_campaign_status(cls, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get the current status of a campaign."""
        campaign = cls._campaigns.get(campaign_id)
        if not campaign:
            return None
        
        return {
            "campaign_id": campaign_id,
            "video_url": campaign.video_url,
            "campaign_type": campaign.campaign_type,
            "batch_size": campaign.batch_size,
            "total_profiles": campaign.total_profiles,
            "completed_profiles": campaign.completed_profiles,
            "pending_profiles": campaign.pending_profiles,
            "running_profiles": campaign.running_profiles,
            "failed_profiles": campaign.failed_profiles,
            "cancelled": campaign.cancelled,
            "created_at": campaign.created_at.isoformat(),
            "profiles": {
                name: {
                    "status": state.status,
                    "started_at": state.started_at.isoformat() if state.started_at else None,
                    "completed_at": state.completed_at.isoformat() if state.completed_at else None,
                    "error": state.error,
                    "actions": state.actions_performed,
                }
                for name, state in campaign.profiles.items()
            }
        }
    
    @classmethod
    def clear_campaign(cls, campaign_id: int) -> bool:
        """Remove a campaign from cache (e.g., when cancelled)."""
        if campaign_id in cls._campaigns:
            del cls._campaigns[campaign_id]
            cls.save_to_file()
            logger.info(f"Campaign {campaign_id} cleared from cache")
            return True
        return False
    
    @classmethod
    def cancel_campaign(cls, campaign_id: int) -> bool:
        """Mark a campaign as cancelled (signals running batches to stop)."""
        if campaign_id in cls._campaigns:
            cls._campaigns[campaign_id].cancelled = True
            cls.save_to_file()
            logger.info(f"Campaign {campaign_id} marked as cancelled")
            return True
        return False
    
    @classmethod
    def is_cancelled(cls, campaign_id: int) -> bool:
        """Check if a campaign has been cancelled."""
        cls._ensure_loaded()
        campaign = cls._campaigns.get(campaign_id)
        if campaign:
            return campaign.cancelled
        return False
    
    @classmethod
    def restart_campaign(cls, campaign_id: int) -> int:
        """
        Restart a cancelled/stopped campaign.
        Resets the cancelled flag and marks failed/cancelled profiles as pending.
        Returns the number of profiles reset.
        """
        campaign = cls._campaigns.get(campaign_id)
        if not campaign:
            return 0
        
        # Reset cancelled flag
        campaign.cancelled = False
        
        # Reset failed profiles back to pending
        reset_count = 0
        for profile in campaign.profiles.values():
            if profile.status in ('failed', 'running'):
                profile.status = 'pending'
                profile.started_at = None
                profile.completed_at = None
                profile.error = None
                reset_count += 1
        
        cls.save_to_file()
        logger.info(f"Campaign {campaign_id} restarted - {reset_count} profiles reset to pending")
        return reset_count
    
    @classmethod
    def get_running_profiles(cls, campaign_id: int) -> list:
        """Get list of currently running profiles (for cleanup on cancel)."""
        campaign = cls._campaigns.get(campaign_id)
        if not campaign:
            return []
        return [name for name, state in campaign.profiles.items() if state.status == 'running']
    
    @classmethod
    def get_all_campaigns(cls) -> Dict[int, Dict[str, Any]]:
        """Get all campaigns in cache (for dashboard)."""
        cls._ensure_loaded()  # Make sure cache is loaded from file
        return {
            cid: cls.get_campaign_status(cid)
            for cid in cls._campaigns.keys()
        }
