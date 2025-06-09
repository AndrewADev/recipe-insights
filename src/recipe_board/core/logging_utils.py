import os
from typing import Callable, Any


def should_log_user_data() -> bool:
    """Check if user data logging is enabled via environment variable."""
    return os.getenv("RB_ALLOW_USER_DATA_LOGS", "false").lower() == "true"


def safe_log_user_data(
    logger_func: Callable[..., Any], message: str, *args, **kwargs
) -> None:
    """Log user data only if enabled, otherwise don't log anything."""
    if should_log_user_data():
        logger_func(message, *args, **kwargs)


def safe_user_data_dict(data: dict) -> dict:
    """Return user data dict if logging enabled, otherwise return empty dict."""
    if should_log_user_data():
        return data
    else:
        return {}
