import os
from typing import Any, Dict, List, Optional

from batchman.models import LocalBatchStatus, ProviderConfig, Request, Result
from batchman.models.batch import Batch


class Provider:
    _registry: Dict[str, type] = {}

    name: str

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config:
            self.config = config
        else:
            # we set the config from env variables at creation time ->
            # avoids improper sync between stored and used config
            api_key = os.getenv(f"{self.name.upper()}_API_KEY", None)
            base_url = os.getenv(f"{self.name.upper()}_BASE_URL", None)
            self.config = ProviderConfig(api_key=api_key, url=base_url)

    @property
    def _api_key(self) -> str:
        if self.config.api_key:
            return self.config.api_key
        else:
            raise ValueError(f"No API key provided for {self.name} provider")

    @property
    def _base_url(self) -> str:
        if self.config.url:
            return self.config.url
        else:
            # A default base url could be provided by providers, so we don't raise an error here
            return None

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._registry.get(name.lower())

    @classmethod
    def available_providers(cls) -> List[type]:
        return [provider for provider in cls._registry.values()]

    def validate_request(self, local_request: Request) -> None:
        """
        Validate a request locally before uploading it to the provider (for example,
        check if the given model is handled by the provider, that the max tokens are
        not too high, etc...).

        raise ValueError
        """
        raise NotImplementedError

    def upload_batch(self, local_batch: Batch) -> str:
        """Upload a batch to the provider.

        This method should upload the batch to the provider and update the local batch state
        accordingly using the Batch methods:
        
        - ``_save_remote_state``
        - ``_save_remote_requests`` (optional)

        The remote state can be the dump of the provider's "status" response.

        Args:
            local_batch (Batch): The batch to be uploaded to the provider.

        Returns:
            str: The remote batch ID.

        Note:
            The local batch state must be updated during this operation.
        """
        raise NotImplementedError

    def cancel_batch(self, local_batch: Batch) -> None:
        raise NotImplementedError

    def sync_batch(self, local_batch: Batch) -> None:
        """
        Sync the local batch state with the provider's state.

        This method should update the local batch state using the Batch methods:

        - ``_save_remote_state``
        """
        raise NotImplementedError

    def download_batch_results(self, local_batch: Batch) -> None:
        raise NotImplementedError

    def convert_batch_status(self, provider_state: Dict[str, Any]) -> LocalBatchStatus:
        """
        Convert the provider's state to a compatible local batch status.

        Args:
            provider_state (Dict[str, Any]): The provider's state, previously saved using ``_save_remote_state``.

        Returns:
            LocalBatchStatus: The batch status.

        Note:
            The local batch status is called local because it is the remote_state stored locally.
        """
        raise NotImplementedError

    def convert_batch_result(self, provider_result: Dict[str, Any]) -> Result:
        """
        Convert the provider's result to a compatible local result.

        Args:
            provider_result (Dict[str, Any]): The provider's result, previously saved using download_batch_results.

        Returns:
            Result: The result.

        Note:
            provider_result will correspond to a single line of the response jsonl file.
        """
        raise NotImplementedError
