from typing import Any, Dict, List, Optional, Union

from batchman.models.request import Request
from batchman.models.provider_config import ProviderConfig
from batchman.models.result import Result
from batchman.models.batch import LocalBatchStatus, Batch
from batchman.utils import upsert_json, read_jsonl, append_jsonl, logger
from batchman.providers.registry import ProviderRegistry


class EditableBatch(Batch):
    """
    Define a Batch in an editable state.
    This represents a Batch object created but not yet uploaded to a provider.
    When the batch is uploaded, the EditableBatch object returns an UploadedBatch object and the EditableBatch
    object is no longer valid.
    """

    def add_metadata(self, metadata: Dict[str, Any]) -> None:
        """Add metadata to the batch."""
        upsert_json(self._files.metadata, metadata)

    def add_requests(self, requests: Union[Request, List[Request]]) -> None:
        """Add one or more requests to the batch."""
        if isinstance(requests, Request):
            requests = [requests]

        append_jsonl(
            self._files.requests, [request.model_dump() for request in requests]
        )

    def override_request_params(self, **kwargs: Any) -> None:
        """Set or update global parameters for all requests in the batch."""
        upsert_json(self._files.global_request_params, kwargs)

    def set_provider(
        self,
        provider: str,
        provider_config: Optional[ProviderConfig] = None,
        prevalidate_requests: bool = True,
    ) -> None:
        """Set the provider for the batch, if not already set.

        Args:
            provider: The name of the provider.
            provider_config: The provider configuration. If not provided, the default config for the provider is used.
            prevalidate_requests: Whether to validate the requests before uploading.

        Raises:
            ValueError: If request validation fails for the new provider, or if provider is not found
        """
        if self.remote_id:
            # should not happen, but just in case
            raise ValueError("Cannot set provider after batch has been uploaded")

        if provider_config is None:
            config_hash = ProviderRegistry.get_default_config_hash(provider)
        else:
            config_hash = ProviderRegistry.store_config(provider_config)

        upsert_json(
            self._files.batch_params,
            {"provider": {"name": provider, "config_hash": config_hash}},
        )

        if prevalidate_requests:
            try:
                self.prevalidate_requests()
            except ValueError as e:
                logger.error(f"Validation Error in set_provider, you can set prevalidate_requests=False, and/or use global_request_params to fix the requests")
                raise e

    def copy(self, new_name: Optional[str] = None, new_unique_id: Optional[str] = None, keep_provider: bool = False) -> "EditableBatch":
        """Copy the batch to a new batch.

        Args:
            new_name: The name of the new batch. Optional, if not provided, the name of the current batch is used.
            new_unique_id: The unique id of the new batch. Optional, if not provided, a new unique id is generated.
            keep_provider: Whether to keep the provider of the current batch. If False, the provider is reset to None.

        Returns:
            EditableBatch: The new batch object.
        """
        new_directory = self._copy_dir(new_name, new_unique_id, keep_provider)
        return EditableBatch.from_directory(self.batcher, new_directory)

    def prevalidate_requests(self) -> None:
        """Pre-validates all requests in the batch against the provider's requirements, before uploading.

        Help filter out requests that will fail to upload (because of missing params, etc).
        It is automatically called before uploading or when setting the provider, but
        can be called manually if you want to check.

        Raises:
            ValueError: If provider is not set or if any requests are invalid
        """
        if not self._provider:
            raise ValueError("Provider not set")

        invalid_requests = []

        for request in self.requests:
            try:
                self._provider.validate_request(request)
            except ValueError as e:
                invalid_requests.append((request, e))

        if len(invalid_requests) > 0:
            raise ValueError(
                "\n".join(
                    [
                        f"- {request.custom_id}: {error}"
                        for request, error in invalid_requests
                    ]
                )
            )

    def upload(self) -> "UploadedBatch":
        """Upload the batch to the provider, and return the uploaded batch object.
        The editable batch object is no longer valid after this operation (because the batch is not
        editable anymore after uploading).

        Raises:
            ValueError: If provider is not set
            RuntimeError: If the batch upload fails
        """
        if not self._provider:
            raise ValueError("Provider not set")

        if self.remote_id:
            logger.warning(
                f"Batch {self.params.name}:{self.unique_id} already uploaded (provider: {self._provider.name}, remote_id: {self.remote_id})"
            )
            return self
        self.prevalidate_requests()
        remote_id = self._provider.upload_batch(self)
        logger.info(f"Batch {self.params.name}:{self.unique_id} uploaded, remote_id: {remote_id})")
        upsert_json(self._files.batch_params, {"remote_id": remote_id})
        if not remote_id:
            raise RuntimeError("Failed to upload batch, no remote id returned")
        return UploadedBatch.from_directory(self.batcher, self.directory)


class UploadedBatch(Batch):
    """
    Define a Batch in an uploaded state.
    This represents a Batch object that has already been uploaded to a provider.
    """

    def __check_correct(self) -> None:
        assert self._provider, "Provider not set"
        assert self.remote_id, "Remote ID not found. Please upload the batch first."

    def sync(self) -> None:
        """Synchronize the local batch state with the remote provider state."""
        self.__check_correct()
        self._provider.sync_batch(self)

    def cancel(self) -> None:
        """Cancel the batch on the remote provider."""
        self.__check_correct()
        self._provider.cancel_batch(self)
        self.sync()

    def copy(self, new_name: Optional[str] = None, new_unique_id: Optional[str] = None, keep_provider: bool = False) -> "EditableBatch":
        """Copy the batch to a new editablebatch.

        It only keeps the requests, the provider config / potentially uploaded data are not copied.
        This allows to easily reupload a batch to a different provider.

        Args:
            new_name: The name of the new batch. Optional, if not provided, the name of the current batch is used.
            new_unique_id: The unique id of the new batch. Optional, if not provided, a new unique id is generated.
            keep_provider: Whether to keep the provider of the current batch. If False, the provider is reset to None.

        Returns:
            EditableBatch: The new editable batch object.
        """
        new_directory = self._copy_dir(new_name, new_unique_id, keep_provider)
        return EditableBatch.from_directory(self.batcher, new_directory)

    def download(self) -> "DownloadedBatch":
        """
        Download results from the remote provider.
        If the batch is not completed, raise an error.

        Returns:
            DownloadedBatch: The downloaded batch object.
        Raises:
            ValueError: If the batch is not completed.
        """
        self.__check_correct()
        self.sync()
        if self.status != LocalBatchStatus.COMPLETED:
            raise ValueError("Batch not completed")
        self._provider.download_batch_results(self)

        return DownloadedBatch.from_directory(self.batcher, self.directory)


class DownloadedBatch(Batch):
    """
    Define a Batch in a downloaded state.
    This represents a Batch object that has already been downloaded from a provider.
    """

    def get_results(self) -> Optional[List[Result]]:
        """
        Returns the results of the batch.

        Returns:
            List[Result]: The results of the batch.
        """
        assert self._provider, "Provider not set"
        assert self.remote_id, "Remote ID not found. Please upload the batch first."

        assert self.status == LocalBatchStatus.DOWNLOADED

        jsonlines = read_jsonl(self._files.remote_results)
        return [self._provider.convert_batch_result(result) for result in jsonlines]

    def copy(self, new_name: Optional[str] = None, new_unique_id: Optional[str] = None, keep_provider: bool = False) -> "EditableBatch":
        """Copy the batch to a new editablebatch.

        It only keeps the requests, the provider config / potential results data are not copied.
        This allows to easily reupload a batch to a different provider.

        Args:
            new_name: The name of the new batch. Optional, if not provided, the name of the current batch is used.
            new_unique_id: The unique id of the new batch. Optional, if not provided, a new unique id is generated.
            keep_provider: Whether to keep the provider of the current batch. If False, the provider is reset to None.

        Returns:
            EditableBatch: The new editable batch object.
        """
        new_directory = self._copy_dir(new_name, new_unique_id, keep_provider)
        return EditableBatch.from_directory(self.batcher, new_directory)
