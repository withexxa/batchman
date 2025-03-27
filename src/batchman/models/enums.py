from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class LocalBatchStatus(str, Enum):
    """Status enumeration for local batch processing.

    This enum tracks the various states a batch can be in during its lifecycle,
    from initialization through completion or failure.

    Attributes:
        INITIALIZING (str): Initial state when batch is being set up, and not yet uploaded
        VALIDATING (str): Batch is uploaded and undergoing validation checks at the provider
        REGISTERED (str): Batch has been successfully registered in the provider system
        IN_PROGRESS (str): Batch is currently being processed
        COMPLETED (str): Batch has finished processing successfully
        CANCELLED (str): Batch was manually cancelled
        FAILED (str): Batch processing encountered an error (not to confuse with failed requests, a batch can be COMPLETED but with some failed requests)
        DOWNLOADED (str): Batch results have been downloaded
    """
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    REGISTERED = "registered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    DOWNLOADED = "downloaded"


class CompletionWindow(str, Enum):
    HOURS_24 = "24h"
    HOURS_48 = "48h"
    HOURS_72 = "72h"
    HOURS_96 = "96h"
    HOURS_120 = "120h"
