from pathlib import Path
from typing import List, Optional, Tuple, Union
from pydantic import ValidationError
import uuid
import shutil

from .providers.registry import ProviderRegistry
from .models.provider_config import ProviderConfig
from .models.batch import Batch
from .models.enums import LocalBatchStatus
from .utils import upsert_json, autoinit
from .utils.logging import logger
from .batch_interfaces import EditableBatch, UploadedBatch, DownloadedBatch


class Batcher:
    """Manage batches of requests on different providers."""

    def __init__(self, batches_dir: Path = Path("batches")):
        if isinstance(batches_dir, str):
            batches_dir = Path(batches_dir)
        batches_dir.mkdir(parents=True, exist_ok=True)
        self.batches_dir = batches_dir

    # NOT UP TO DATE
    # @autoinit
    # def register_remote_batch(
    #     self, provider: str, provider_config: ProviderConfig, remote_id: str
    # ) -> UploadedBatch:
    #     if provider:
    #         provider_is_registered = ProviderRegistry.is_registered(provider)

    #         if not provider_is_registered:
    #             raise ValueError(f"Provider {provider} not found")

    #     batch = UploadedBatch(Batch(self, name=f"external-{provider}", unique_id=remote_id))
    #     # TODO: fix, this doesn't seems to use the same config_hash parameter as created batch
    #     upsert_json(
    #         batch._batch_implem.files.batch_params,
    #         {
    #             "provider": {"name": provider, "config": provider_config},
    #             "remote_id": remote_id,
    #         },
    #     )
    #     return batch

    def create_batch(
        self,
        name: str,
        unique_id: Optional[str] = None,
        provider: Optional[str] = None,
        provider_config: Optional[ProviderConfig] = None,
    ) -> EditableBatch:
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
        if provider:
            provider_is_registered = ProviderRegistry.is_registered(provider)

            if not provider_is_registered:
                raise ValueError(f"Provider {provider} not found")

        if not unique_id:
            unique_id = str(uuid.uuid4())

        # Check if batch already exists
        dir_name = f"batch-{name}-{unique_id}"
        if (self.batches_dir / dir_name).exists():
            raise FileExistsError(f"Batch with name '{name}' and ID '{unique_id}' already exists,"
                             " use load_batch to load it or use a different unique_id to create a new batch")

        return EditableBatch(
            batcher=self,
            name=name,
            unique_id=unique_id,
            provider=provider,
            provider_config=provider_config,
        )

    def load_batch(self, unique_id: str, name: Optional[str] = None) -> Union[EditableBatch, UploadedBatch, DownloadedBatch]:
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
        if unique_id is None:
            raise ValueError("unique_id must be provided")

        if name is not None:
            dir_name = f"batch-{name}-{unique_id}"
            batch_dir = self.batches_dir / dir_name
            if not batch_dir.exists():
                raise FileNotFoundError(f"Batch with name '{name}' and ID '{unique_id}' does not exist")
        else:
            # Search for batch with matching unique_id
            matching_dirs = list(self.batches_dir.glob(f"batch-*-{unique_id}"))
            if not matching_dirs:
                raise FileNotFoundError(f"No batch found with ID '{unique_id}'")
            if len(matching_dirs) > 1:
                raise RuntimeError(f"Multiple batches found with ID '{unique_id}'")
            batch_dir = matching_dirs[0]
            logger.debug(f"Found batch {batch_dir} with ID '{unique_id}'")

        batch = Batch.from_directory(self, batch_dir)
        if batch.remote_id is None:
            return EditableBatch.from_directory(self, batch_dir)
        elif batch._files.remote_results.exists():
            return DownloadedBatch.from_directory(self, batch_dir)
        else:
            return UploadedBatch.from_directory(self, batch_dir)

    def list_batches(self) -> Tuple[List[EditableBatch], List[UploadedBatch], List[DownloadedBatch], List[str]]:
        """List all batches in the batches directory in a error resilient way.

    Returns:
        A tuple containing:
        - List of successfully loaded EditableBatch instances
        - List of successfully loaded UploadedBatch instances
        - List of successfully loaded DownloadedBatch instances
        - List of errors that occurred while loading the batches
    """

        errors = []
        editable_batches = []
        uploaded_batches = []
        downloaded_batches = []
        for batch_dir in self.batches_dir.iterdir():
            try:
                batch = Batch.from_directory(self, batch_dir)
                if batch.remote_id is None:
                    editable_batches.append(EditableBatch.from_directory(self, batch_dir))
                elif batch._files.remote_results.exists():
                    downloaded_batches.append(DownloadedBatch.from_directory(self, batch_dir))
                else:
                    uploaded_batches.append(UploadedBatch.from_directory(self, batch_dir))
            except KeyError as e:
                errors.append(f"KeyError loading batch from {batch_dir}, missing key: {e}")
            except Exception as e:
                errors.append(f"Error loading batch from {batch_dir}: {e}")
        return editable_batches, uploaded_batches, downloaded_batches, errors

    def sync_batches(self) -> List[str]:
        """Sync all batches in the batches directory in a error resilient way.

    Returns:
        List of errors with the batch directory and the corresponding exception
    """

        # no need to sync editable batches (they are not uploaded), and downloaded batches are already synced
        _, uploaded_batches, _, errors = self.list_batches()

        for batch in uploaded_batches:
            try:
                batch.sync()
                if batch.status == LocalBatchStatus.COMPLETED:
                    batch.download()

            except Exception as e:
                errors.append(
                    f"Error syncing batch {batch.params.name}:{batch.unique_id}: {e}"
                )

        return errors

    def _rm_batch_dir(self, im_sure_to_delete_all_batches: bool = False) -> None:
        """Remove the batches directory and all its contents.

            The batcher is no longer usable after this.
            It's only useful for testing purposes.

        Args:
            im_sure_to_delete_all_batches: If True, the user will not be asked for confirmation

        To make it not visible in the generated doc
        :meta private:
        """
        if not self.batches_dir.exists():
            return

        if not im_sure_to_delete_all_batches:
            if input(f"Are you sure you want to delete {self.batches_dir}? This will delete all batches in this directory [y/N] ").lower() != "y":
                return
        shutil.rmtree(self.batches_dir)
