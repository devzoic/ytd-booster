"""
Profile data models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    """Request model for creating profiles."""
    
    device_id: int = Field(..., description="Device ID from Laravel")
    user_id: int = Field(..., description="User ID from Laravel")
    count: int = Field(default=1, ge=1, le=100, description="Number of profiles to create")
    browser_type: str = Field(default="chrome", description="Browser type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": 1,
                "user_id": 1,
                "count": 5,
                "browser_type": "chrome"
            }
        }


class ProfileData(BaseModel):
    """Profile data structure."""
    
    id: Optional[int] = None
    name: str
    device_id: int
    user_id: int
    status: str = "ready"
    browser_type: str = "chrome"
    profile_path: str
    fingerprint: Optional[Dict[str, Any]] = None
    os_platform: Optional[str] = None  # windows, macos, linux, android
    browser_version: Optional[str] = None  # Chrome version (e.g., "124")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Profile_1705286400_1",
                "device_id": 1,
                "user_id": 1,
                "status": "ready",
                "browser_type": "chrome",
                "profile_path": "/profiles_data/device_1/profile_1",
                "fingerprint": {"user_agent": "..."},
                "created_at": "2024-01-15T00:00:00"
            }
        }


class ProfileResponse(BaseModel):
    """Response model for profile operations."""
    
    success: bool
    message: str
    profiles: List[ProfileData] = []
    count: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "5 profiles created successfully",
                "profiles": [],
                "count": 5
            }
        }


class ProfileDeleteRequest(BaseModel):
    """Request model for bulk profile deletion."""
    
    profile_ids: List[int] = Field(..., description="List of profile IDs to delete")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_ids": [1, 2, 3]
            }
        }
