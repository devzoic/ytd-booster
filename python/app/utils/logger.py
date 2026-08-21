"""
Logging configuration.
"""

import logging
import sys
from typing import Optional, List


# In-memory log buffer for dashboard streaming
_log_buffer: List[str] = []
MAX_LOG_BUFFER = 500


class DashboardLogHandler(logging.Handler):
    """Custom handler that pushes logs to dashboard buffer for real-time viewing."""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            _log_buffer.append(msg)
            # Keep buffer from growing too large
            if len(_log_buffer) > MAX_LOG_BUFFER:
                _log_buffer.pop(0)
        except Exception:
            self.handleError(record)


def get_log_buffer() -> List[str]:
    """Get the current log buffer for dashboard."""
    return _log_buffer.copy()


def clear_log_buffer():
    """Clear the log buffer."""
    global _log_buffer
    _log_buffer = []


def setup_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name. If None, returns root logger.
        level: Logging level.
    
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Dashboard handler for real-time log streaming
        dashboard_handler = DashboardLogHandler()
        dashboard_handler.setLevel(level)
        dashboard_handler.setFormatter(formatter)
        logger.addHandler(dashboard_handler)
    
    return logger
