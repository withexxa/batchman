import json
import os
import time
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from pydantic_core import to_jsonable_python

from ..utils import logger
from ..models.enums import LocalBatchStatus
from ..models.request import Request
from ..models.batch import Batch
from ..models.result import Result
from .base import Provider

from openai import OpenAI


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        start = time.time()
        self.__models = [model.id for model in self.client.models.list()]
        end = time.time()
        logger.debug(f"[OpenAI] Models loaded in {end - start} seconds")

    def _prepare_request(self, request: Request) -> Dict[str, Any]:
        metadata = {
            "custom_id": request.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
        }

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
                {
                    "role": message.role,
                    "content": to_jsonable_python(message.content),
                }
            )

        request_body: Dict[str, Any] = {
            "messages": messages,
        }

        if request.model:
            request_body["model"] = request.model

        if request.max_tokens:
            request_body["max_completion_tokens"] = request.max_tokens

        for param in ["temperature", "top_p"]:
            param_value = getattr(request, param)

            if param_value:
                request_body[param] = param_value

        return {**metadata, "body": request_body}

    def validate_request(self, local_request: Request) -> None:
        if not local_request.model:
            raise ValueError("Model is required")
        if local_request.model not in self.__models:
            raise ValueError(f"Model {local_request.model} is not available on OpenAI")

    def upload_batch(self, local_batch: Batch) -> str:
        # Create a temporary file to store batch requests
        with NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as temp_file:
            # Write each request to the temp file
            for request in local_batch.requests:
                prepared_request = self._prepare_request(request)
                json.dump(prepared_request, temp_file)
                temp_file.write("\n")

            temp_file.flush()  # Ensure that all writes are flushed to disk

            try:
                logger.debug("[OpenAI] Uploading batch file")

                with open(temp_file.name, "rb") as file:
                    batch_file = self.client.files.create(file=file, purpose="batch")

                # If it succeeded, copy the temp file in the batch directory
                with open(temp_file.name, "r") as file:
                    local_batch._save_remote_requests(file.read())

                logger.debug("[OpenAI] Creating batch")

                remote_batch = self.client.batches.create(
                    input_file_id=batch_file.id,
                    endpoint="/v1/chat/completions",
                    completion_window=local_batch.params.completion_window,
                    metadata=local_batch.metadata,
                )

                logger.debug("[OpenAI] Batch uploaded")

                local_batch._save_remote_state(remote_batch.model_dump())

                return remote_batch.id
            finally:
                # Clean up - remove the temporary file
                os.unlink(temp_file.name)

    def cancel_batch(self, local_batch: Batch) -> None:
        try:
            remote_batch = self.client.batches.cancel(local_batch.params.remote_id)
            local_batch._save_remote_state(remote_batch.model_dump())
        except Exception as e:
            raise ValueError(f"Failed to cancel batch: {e}")

    def sync_batch(self, local_batch: Batch) -> None:
        try:
            remote_batch = self.client.batches.retrieve(local_batch.remote_id)
            local_batch._save_remote_state(remote_batch.model_dump())
        except Exception as e:
            raise ValueError(f"Failed to sync batch: {e}")

    def download_batch_results(self, local_batch: Batch) -> None:
        try:
            remote_batch = self.client.batches.retrieve(local_batch.remote_id)
            local_batch._save_remote_state(remote_batch.model_dump())

            # if remote_batch.errors:

            if remote_batch.status == "completed":
                output_file_id = remote_batch.output_file_id
                output_file = self.client.files.content(output_file_id)
                results = output_file.text
                errors_file_id = remote_batch.error_file_id
                if errors_file_id:
                    errors_file = self.client.files.content(errors_file_id)
                    results = results + errors_file.text

                local_batch._save_remote_results(results)

                logger.debug("[OpenAI] Batch results downloaded")
        except Exception as e:
            raise ValueError(f"Failed to download batch results: {e}")

    def convert_batch_status(self, remote_state: Dict[str, Any]) -> LocalBatchStatus:
        status = remote_state["status"]

        if status == "completed":
            return LocalBatchStatus.COMPLETED
        elif status == "cancelled":
            return LocalBatchStatus.CANCELLED
        elif status == "cancelling":
            return LocalBatchStatus.CANCELLED
        elif status == "validating":
            return LocalBatchStatus.VALIDATING
        elif status == "registered":
            return LocalBatchStatus.REGISTERED
        elif status == "in_progress":
            return LocalBatchStatus.IN_PROGRESS
        else:
            raise ValueError(f"Unknown batch status: {status}")

    def convert_batch_result(self, result: Dict[str, Any]) -> Result:
        if "error" in result["response"]["body"]:
            return Result(
                custom_id=result["custom_id"],
                choices=[],
                usage=None,
                error=str(result["response"]["body"]["error"]),
            )
        return Result(
            custom_id=result["custom_id"],
            choices=result["response"]["body"]["choices"],
            usage=result["response"]["body"]["usage"],
            error=None,
        )
