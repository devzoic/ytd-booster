"""
Campaign execution configuration with adaptive batch sizing.
"""

from typing import Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CampaignConfig:
    """Configuration for campaign execution with intelligent resource management."""
    
    # Default batch size (can be overridden per campaign)
    DEFAULT_BATCH_SIZE = 5
    
    # Delay between batches (seconds)
    BATCH_DELAY = 3
    
    # Delay between opening tabs within a batch (seconds)
    TAB_OPEN_DELAY = 1.5
    
    # Delay between actions (like/comment) within a batch (seconds)
    ACTION_DELAY = 0.5
    
    # Minimum/Maximum batch sizes for auto-detection
    MIN_BATCH_SIZE = 2
    MAX_BATCH_SIZE = 15
    
    # RAM thresholds for batch size calculation (GB)
    RAM_THRESHOLDS = [
        (4, 3),    # < 4GB RAM → 3 profiles
        (8, 5),    # < 8GB RAM → 5 profiles
        (16, 8),   # < 16GB RAM → 8 profiles
        (32, 12),  # < 32GB RAM → 12 profiles
    ]
    
    @classmethod
    def get_optimal_batch_size(cls) -> int:
        """
        Calculate optimal batch size based on available system RAM.
        
        Returns:
            int: Recommended batch size for current system resources
        """
        try:
            import psutil
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
            
            # Find appropriate batch size based on RAM
            for threshold, batch_size in cls.RAM_THRESHOLDS:
                if available_ram_gb < threshold:
                    logger.info(f"Auto-detected batch size: {batch_size} (available RAM: {available_ram_gb:.1f} GB)")
                    return batch_size
            
            # High RAM system
            batch_size = cls.MAX_BATCH_SIZE
            logger.info(f"Auto-detected batch size: {batch_size} (high RAM system: {available_ram_gb:.1f} GB)")
            return batch_size
            
        except ImportError:
            logger.warning("psutil not installed, using default batch size")
            return cls.DEFAULT_BATCH_SIZE
        except Exception as e:
            logger.warning(f"Error detecting system resources: {e}, using default batch size")
            return cls.DEFAULT_BATCH_SIZE
    
    @classmethod
    def get_batch_size(cls, campaign_batch_size: Optional[int] = None) -> int:
        """
        Get the batch size to use for a campaign.
        
        Priority:
        1. Campaign-specific batch size (if provided and valid)
        2. Auto-detected based on system resources
        
        Args:
            campaign_batch_size: Optional batch size specified for the campaign
            
        Returns:
            int: Batch size to use
        """
        if campaign_batch_size and campaign_batch_size > 0:
            # Clamp to valid range
            batch_size = max(cls.MIN_BATCH_SIZE, min(campaign_batch_size, cls.MAX_BATCH_SIZE))
            logger.info(f"Using campaign-specified batch size: {batch_size}")
            return batch_size
        
        # Auto-detect
        return cls.get_optimal_batch_size()
