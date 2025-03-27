from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel

from ..models import CompletionWindow, LocalBatchStatus, Request, ProviderConfig, Result

from ..utils.logging import logger
from ..utils.files import append_jsonl, read_json, read_jsonl, upsert_json, write_jsonl
from ..providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from ..batchman import Batcher
    from ..providers.base import Provider


class BatchParams(BaseModel):
    name: str
    unique_id: str
    provider: Dict[str, Any]
    remote_id: Optional[str]
    completion_window: CompletionWindow


class BatchFiles:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

        self.remote_states = self.directory / "remote_states.jsonl"
        self.remote_requests = self.directory / "remote_requests.jsonl"
        self.remote_results = self.directory / "remote_results.jsonl"

        self.requests = self.directory / "requests.jsonl"

        self.metadata = self.directory / "batch_metadata.json"
        self.batch_params = self.directory / "batch_params.json"
        self.global_request_params = self.directory / "global_request_params.json"


class Batch:
    def __init__(
        self,
        batcher: "Batcher",
        name: str,
        unique_id: Optional[str] = None,
        provider: Optional[str] = None,
        provider_config: Optional[ProviderConfig] = None,
        completion_window: CompletionWindow = CompletionWindow.HOURS_24,
    ) -> None:
        self.batcher = batcher
        self.unique_id = unique_id or str(uuid4())
        self.directory: Path = batcher.batches_dir / f"batch-{name}-{self.unique_id}"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.__provider_instance = None

        if not self._files.batch_params.exists():
            provider_config_hash = None
            if provider_config:
                provider_config_hash = ProviderRegistry.store_config(provider_config)
            elif provider:
                # if a provider is given but no config, we get the default one for this provider
                provider_config_hash = ProviderRegistry.get_default_config_hash(provider)

            self._batch_params: BatchParams = BatchParams(
                name=name,
                unique_id=self.unique_id,
                provider={"name": provider, "config_hash": provider_config_hash},
                remote_id=None,
                completion_window=completion_window,
            )
            upsert_json(self._files.batch_params, self._batch_params)

        if not self._files.metadata.exists():
            upsert_json(self._files.metadata, {})

        if not self._files.global_request_params.exists():
            upsert_json(self._files.global_request_params, {})

    @classmethod
    def from_directory(cls, batcher: "Batcher", directory: Path) -> "Batch":
        if not directory.exists():
            raise ValueError(f"Directory {directory} does not exist")

        batch_files = BatchFiles(directory=directory)
        params = read_json(batch_files.batch_params)

        return cls(batcher, params["name"], params["unique_id"], params["provider"])

    def _copy_dir(self, new_name: Optional[str] = None, new_unique_id: Optional[str] = None, keep_provider: bool = False) -> Path:
        import shutil
        new_name = new_name or self.params.name
        new_unique_id = new_unique_id or str(uuid4())
        batch = Batch(self.batcher, new_name, new_unique_id)

        if keep_provider:
            upsert_json(batch._files.batch_params, {"provider": self.params.provider})

        if self._files.requests.exists():
            shutil.copy(self._files.requests, batch._files.requests)
        if self._files.global_request_params.exists():
            shutil.copy(self._files.global_request_params, batch._files.global_request_params)
        if self._files.metadata.exists():
            shutil.copy(self._files.metadata, batch._files.metadata)

        return batch._files.directory

    @property
    def _files(self) -> BatchFiles:
        return BatchFiles(directory=self.directory)

    @property
    def params(self) -> BatchParams:
        data = read_json(self._files.batch_params)
        return BatchParams(**data)

    @property
    def metadata(self) -> Dict[str, Any]:
        return read_json(self._files.metadata)

    @property
    def global_request_params(self) -> Dict[str, Any]:
        """Global parameters, will override request params on each request in the batch"""
        return read_json(self._files.global_request_params)

    @property
    def requests(self) -> List[Request]:
        """Return all requests in the batch as a jsonl, with global params applied"""
        jsonlines = read_jsonl(self._files.requests)
        # Merge global params with request params (global params override request params)
        return [
            Request(**{**request, **self.global_request_params})
            for request in jsonlines
        ]

    @property
    def _remote_state(self) -> Optional[Dict[str, Any]]:
        try:
            last_remote_state = read_jsonl(self._files.remote_states)
        except FileNotFoundError:
            return None

        if len(last_remote_state) == 0:
            return None

        return last_remote_state[-1]

    @property
    def status(self) -> LocalBatchStatus:
        # If there is no remote file, the batch is pending
        if not self._remote_state or not self._provider:
            return LocalBatchStatus.INITIALIZING

        status = self._provider.convert_batch_status(self._remote_state)

        if status == LocalBatchStatus.COMPLETED and self._files.remote_results.exists():
            return LocalBatchStatus.DOWNLOADED

        return status

    @property
    def remote_id(self) -> Optional[str]:
        state = self._remote_state

        # If the remote state is not found, the batch is not uploaded even if the remote_id is set locally
        if not state:
            return None

        return self.params.remote_id

    @property
    def _provider(self) -> Optional["Provider"]:
        if self.__provider_instance:
            return self.__provider_instance

        provider_dict = self.params.provider

        provider_name = provider_dict.get("name", None)
        provider_config_hash = provider_dict.get("config_hash", None)

        if not provider_name:
            return None

        provider_cls = ProviderRegistry.get(provider_name)
        if not provider_cls:
            return None

        provider_config = ProviderRegistry.get_stored_config(provider_config_hash)
        if not provider_config and provider_config_hash:
            raise ValueError(
                f"Provider config not found for hash {provider_config_hash}"
            )

        self.__provider_instance = provider_cls(config=provider_config)
        return self.__provider_instance

    def _save_remote_requests(self, content: Union[List[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Save remote requests to a JSONL file."""
        write_jsonl(self._files.remote_requests, content)

    def _save_remote_results(self, content: Union[List[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Save remote results to a JSONL file."""
        write_jsonl(self._files.remote_results, content)

    def _save_remote_state(self, content: Dict[str, Any]) -> None:
        """Append remote state to a JSONL file."""
        append_jsonl(self._files.remote_states, content)

    def __str__(self) -> str:
        return f"{type(self).__name__} (name={self.params.name}, remote_id={self.params.remote_id}, status={self.status}, provider={self.params.provider})"
