import os
from typing import TYPE_CHECKING, Any, Dict, Optional
from pydantic_core import to_jsonable_python
import requests as http_client

from ..utils.logging import logger

from ..models.dataclasses import Choice
from ..models.result import Result
from ..models.enums import LocalBatchStatus
from ..models.provider_config import ProviderConfig
from .base import Provider

if TYPE_CHECKING:
    from ..models.batch import Batch
    from ..models.request import Request


class ExxaProvider(Provider):
    _BASE_URL = "https://api.withexxa.com/v1"

    name = "exxa"

    def __init__(self, config: Optional[ProviderConfig] = None):
        # exemple of how to override the default configuration
        super().__init__(config)
        if not self.config.url:
            self.config.url = self._BASE_URL

    def validate_request(self, request: "Request") -> None:
        errors = []

        request_dict = request.model_dump()

        if "model" not in request_dict:
            errors.append("model is required")
        if "custom_id" not in request_dict:
            errors.append("custom_id is required")
        if "messages" not in request_dict:
            errors.append("messages are required")
        if len(request_dict["messages"]) == 0:
            errors.append("messages cannot be empty")

        if len(errors) > 0:
            raise ValueError("\n".join(errors))

    def _prepare_request(self, request: "Request") -> Dict[str, Any]:
        metadata = {"custom_id": request.custom_id}

        metadata_dict = request.metadata

        if metadata_dict:
            metadata.update(metadata_dict)

        messages = []

        if request.system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": request.system_prompt,
                }
            )

        for message in request.messages:
            messages.append(
                {"role": message.role, "content": to_jsonable_python(message.content)}
            )

        request_body: Dict[str, Any] = {}
        request_body["messages"] = messages
        request_body["model"] = request.model

        for param in ["temperature", "top_p", "max_tokens"]:
            param_value = getattr(request, param)

            if param_value:
                request_body[param] = param_value

        return {"metadata": metadata, "request_body": request_body}

    def upload_batch(self, local_batch: "Batch") -> str:
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}

        logger.info(
            f"[Exxa] Uploading batch to {self._base_url} with API key {self._api_key}"
        )

        requests_remote_ids = []

        logger.info("[Exxa] Creating batch")

        for request in local_batch.requests:
            prepared_request = self._prepare_request(request)

            request_response = http_client.post(
                f"{self._base_url}/requests",
                json=prepared_request,
                headers=headers,
            )

            try:
                request_response.raise_for_status()
            except http_client.exceptions.HTTPError as e:
                raise ValueError(
                    f"Failed to upload request: {e}\n{request_response.text}"
                )

            requests_remote_ids.append(request_response.json()["id"])

        batch_response = http_client.post(
            f"{self._base_url}/batches",
            json={"requests_ids": requests_remote_ids},
            headers=headers,
        )

        try:
            batch_response.raise_for_status()

            response = batch_response.json()

            if response["status"] == "registered" and isinstance(response["id"], str):
                logger.info("[Exxa] Batch uploaded")

                local_batch._save_remote_state(response)

                return response["id"]
            else:
                raise ValueError(f"Failed to create batch: {response}")
        except http_client.exceptions.HTTPError as e:
            raise ValueError(f"Failed to create batch: {e}\n{batch_response.text}")

    def cancel_batch(self, local_batch: "Batch") -> None:
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}

        batch_response = http_client.post(
            f"{self._base_url}/batches/{local_batch.params.remote_id}/cancel",
            headers=headers,
        )

        try:
            batch_response.raise_for_status()
        except http_client.exceptions.HTTPError as e:
            raise ValueError(f"Failed to cancel batch: {e}\n{batch_response.text}")

    def sync_batch(self, local_batch: "Batch"):
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}

        batch_response = http_client.get(
            f"{self._base_url}/batches/{local_batch.remote_id}",
            headers=headers,
        )

        try:
            batch_response.raise_for_status()

            local_batch._save_remote_state(batch_response.json())
        except http_client.exceptions.HTTPError as e:
            raise ValueError(f"Failed to sync batch: {e}\n{batch_response.text}")

    def download_batch_results(self, local_batch: "Batch") -> None:
        headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}

        batch_response = http_client.get(
            f"{self._base_url}/batches/{local_batch.params.remote_id}/results",
            headers=headers,
        )

        try:
            batch_response.raise_for_status()
        except http_client.exceptions.HTTPError as e:
            raise ValueError(
                f"Failed to download batch results: {e}\n{batch_response.text}"
            )

        local_batch._save_remote_results(batch_response.text)

    def convert_batch_status(self, remote_state: Dict[str, Any]) -> LocalBatchStatus:
        batch_status = remote_state["status"]

        if batch_status == "completed":
            return LocalBatchStatus.COMPLETED
        elif batch_status == "failed":
            return LocalBatchStatus.FAILED
        elif batch_status == "cancelled":
            return LocalBatchStatus.CANCELLED
        elif batch_status == "registered":
            return LocalBatchStatus.REGISTERED
        elif batch_status == "in_progress":
            return LocalBatchStatus.IN_PROGRESS
        else:
            raise ValueError(f"Unknown batch status: {batch_status}")

    def convert_batch_result(self, provider_result: Dict[str, Any]) -> Result:
        custom_id = provider_result["metadata"]["custom_id"]
        result_body = provider_result["result_body"]

        choices = [Choice(**choice) for choice in result_body["choices"]]
        usage = result_body["usage"]

        error = provider_result.get("error", None)

        return Result(
            custom_id=custom_id,
            choices=choices,
            usage=usage,
            error=error,
        )
