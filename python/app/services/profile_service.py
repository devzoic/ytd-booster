"""
Profile service for managing Chrome automation profiles.
"""

import time
from typing import List, Optional
from pathlib import Path

from app.config import settings
from app.models.profile import ProfileCreate, ProfileData, ProfileResponse
from app.services.browser_service import BrowserService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProfileService:
    """Service for profile CRUD operations."""
    
    def __init__(self):
        self.browser_service = BrowserService()
    
    def create_profiles(self, request: ProfileCreate) -> ProfileResponse:
        """
        Create multiple Chrome profiles.
        
        Args:
            request: Profile creation request with device_id, user_id, count
            
        Returns:
            ProfileResponse with created profiles
        """
        created_profiles: List[ProfileData] = []
        timestamp = int(time.time())
        
        logger.info(f"Creating {request.count} profiles for device {request.device_id}")
        
        for i in range(1, request.count + 1):
            try:
                # Generate profile name
                profile_name = f"Profile_{timestamp}_{i}"
                
                # Create profile directory
                profile_path = BrowserService.create_profile_directory(
                    device_id=request.device_id,
                    profile_name=profile_name
                )
                
                # Generate fingerprint
                fingerprint = BrowserService.generate_fingerprint()
                
                # Save fingerprint to profile directory
                BrowserService.save_fingerprint(profile_path, fingerprint)
                
                # Create profile data
                profile = ProfileData(
                    name=profile_name,
                    device_id=request.device_id,
                    user_id=request.user_id,
                    status="ready",
                    browser_type=request.browser_type,
                    profile_path=str(profile_path),
                    fingerprint=fingerprint,
                    os_platform=fingerprint.get("os_platform") if fingerprint else None,
                    browser_version=fingerprint.get("browser_version") if fingerprint else None
                )
                
                created_profiles.append(profile)
                logger.info(f"Created profile: {profile_name}")
                
            except Exception as e:
                logger.error(f"Failed to create profile {i}: {e}")
                continue
        
        return ProfileResponse(
            success=True,
            message=f"{len(created_profiles)} profile(s) created successfully",
            profiles=created_profiles,
            count=len(created_profiles)
        )
    
    def get_profile(self, profile_path: str) -> Optional[ProfileData]:
        """
        Get profile data by path.
        
        Args:
            profile_path: Path to profile directory
            
        Returns:
            ProfileData or None
        """
        path = Path(profile_path)
        if not path.exists():
            return None
        
        fingerprint = BrowserService.load_fingerprint(path)
        
        return ProfileData(
            name=path.name,
            device_id=0,  # Would need to be stored/retrieved
            user_id=0,
            profile_path=str(path),
            fingerprint=fingerprint
        )
    
    def delete_profile(self, profile_path: str) -> bool:
        """
        Delete a profile.
        
        Args:
            profile_path: Path to profile directory
            
        Returns:
            True if deleted successfully
        """
        return BrowserService.delete_profile_directory(profile_path)
    
    def list_profiles(self, device_id: Optional[int] = None) -> List[ProfileData]:
        """
        List all profiles, optionally filtered by device.
        
        Args:
            device_id: Optional device ID filter
            
        Returns:
            List of profiles
        """
        profiles: List[ProfileData] = []
        
        if device_id:
            device_path = settings.PROFILES_DIR / f"device_{device_id}"
            if device_path.exists():
                for profile_dir in device_path.iterdir():
                    if profile_dir.is_dir():
                        fingerprint = BrowserService.load_fingerprint(profile_dir)
                        profiles.append(ProfileData(
                            name=profile_dir.name,
                            device_id=device_id,
                            user_id=0,
                            profile_path=str(profile_dir),
                            fingerprint=fingerprint
                        ))
        else:
            # List all
            for device_dir in settings.PROFILES_DIR.iterdir():
                if device_dir.is_dir() and device_dir.name.startswith("device_"):
                    dev_id = int(device_dir.name.replace("device_", ""))
                    for profile_dir in device_dir.iterdir():
                        if profile_dir.is_dir():
                            fingerprint = BrowserService.load_fingerprint(profile_dir)
                            profiles.append(ProfileData(
                                name=profile_dir.name,
                                device_id=dev_id,
                                user_id=0,
                                profile_path=str(profile_dir),
                                fingerprint=fingerprint
                            ))
        
        return profiles


# Singleton instance
profile_service = ProfileService()
