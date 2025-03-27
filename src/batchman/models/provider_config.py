from typing import Any, Dict, Optional
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    """Configuration for a provider instance.

    This model holds the configuration needed to initialize and authenticate with a provider.
    Includes API keys and base URLs, and provider specific parameters can be passed in kwargs.

    Example:
        >>> config = ProviderConfig(
        ...     api_key="sk-...",
        ...     url="https://api.example.com",
        ...     kwargs={"organization": "org-123"}
        ... )
    """

    api_key: Optional[str] = None
    """The authentication key for the provider's API."""

    url: Optional[str] = None
    """The base URL for the provider's API endpoints."""

    kwargs: Optional[Dict[str, Any]] = None
    """Additional provider-specific configuration parameters."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "api_key": "sk-abcdef123456",
                "url": "https://api.provider.com/v1",
                "kwargs": {
                    "organization": "org-123",
                    "timeout": 30
                }
            }
        }
    }
