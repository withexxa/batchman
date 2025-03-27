from .batchman import Batcher
from .cli import cli
from .models import Request, UserMessage, ProviderConfig, LocalBatchStatus
from .batch_interfaces import EditableBatch, UploadedBatch, DownloadedBatch
from typing import Optional, Union, List, Tuple


_default_batcher = Batcher()


def create_batch(name: str, unique_id: Optional[str] = None, provider: Optional[str] = None, provider_config: Optional[ProviderConfig] = None) -> "EditableBatch":
    """
    Create a new batch.

    Args:
        name: The name of the batch
        unique_id: The unique ID of the batch. If not provided, a random UUID will be generated
        provider: The name of the provider to use for the batch
        provider_config: The configuration for the provider

    Returns:
        The created batch

    Raises:
        FileExistsError: If the batch already exists
        ValueError: If provider is not found
    """
    return _default_batcher.create_batch(name, unique_id, provider, provider_config)

def load_batch(unique_id: str, name: Optional[str] = None) -> Union[EditableBatch, UploadedBatch, DownloadedBatch]:
    """Load a batch.

    Args:
        unique_id: The unique ID of the batch
        name: The name of the batch (optional)

    Returns:
        The loaded batch, which can be either an EditableBatch, UploadedBatch, or DownloadedBatch

    Raises:
        FileNotFoundError: If the batch does not exist
        ValueError: If neither name nor unique_id is provided
        RuntimeError: If multiple batches are found with the same unique_id
    """
    return _default_batcher.load_batch(unique_id, name)

def list_batches() -> Tuple[List[EditableBatch], List[UploadedBatch], List[DownloadedBatch], List[str]]:
    """List all batches in the batches directory in a error resilient way.

    Returns:
        A tuple containing:
        - List of successfully loaded EditableBatch instances
        - List of successfully loaded UploadedBatch instances
        - List of successfully loaded DownloadedBatch instances
        - List of errors that occurred while loading the batches
    """
    return _default_batcher.list_batches()

def sync_batches() -> None:
    """Sync all batches in the batches directory in a error resilient way.

    Returns:
        List of errors with the batch directory and the corresponding exception
    """
    return _default_batcher.sync_batches()

__all__ = ["Batcher", "Request", "UserMessage", "cli", "EditableBatch", "UploadedBatch", "DownloadedBatch", "ProviderConfig", "LocalBatchStatus"]
