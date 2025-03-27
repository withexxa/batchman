from typing import Any, Dict, List, cast
import anthropic
from pydantic_core import to_jsonable_python

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request as AnthropicRequest
from anthropic.types.messages.message_batch_individual_response import MessageBatchIndividualResponse

from ..utils.logging import logger
from ..models import LocalBatchStatus, Request, Result
from ..models.dataclasses import Choice, AssistantMessage, TextContent
from ..providers.base import Provider

from ..models.batch import Batch


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = anthropic.Anthropic(api_key=self._api_key, base_url=self._base_url)
        self.models = [model.id for model in self.client.models.list()]

    def validate_request(self, local_request: Request) -> None:
        """Validate request parameters for Anthropic."""
        # "-latest" models are supported but not listed in Anthropic's API, so we add them to the list of valid models
        latest_models = [model_id+"latest" for model_id in set([model_id[:-8] for model_id in self.models if model_id[-8:].isdigit()])]
        if local_request.model not in self.models+latest_models:
            raise ValueError(
                f"Invalid model {local_request.model} for Anthropic provider. "
                f"Model name should be one of the following: {self.models} "
                f"Although not recommended for production, it could also be one of the following: {latest_models}"
            )

        if not local_request.max_tokens:
            raise ValueError("max_tokens is required")

        # Anthropic has a max token limit of 200k for input+output
        if local_request.max_tokens > 200000:
            raise ValueError(
                f"max_tokens {local_request.max_tokens} exceeds Anthropic's limit of 200000"
            )

    def _prepare_request(self, request: Request) -> AnthropicRequest:
        if any((request.frequency_penalty, request.presence_penalty, request.n)):
            logger.warning("Anthropic does not support frequency_penalty, presence_penalty, or n,"
                           " these parameters will be ignored")
        return AnthropicRequest(
            custom_id=request.custom_id,
            params={ k:v for k,v in MessageCreateParamsNonStreaming(
                model=request.model,
                messages=to_jsonable_python(request.messages),
                system=request.system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stop_sequences=request.stop,
                metadata=request.metadata
            ).items() if v is not None}
        )

    def upload_batch(self, local_batch: Batch) -> str:
        """Upload a batch to Anthropic.
        """
        temp_requests = [self._prepare_request(req) for req in local_batch.requests]
        message_batch = self.client.messages.batches.create(
            requests=temp_requests
        )
        local_batch._save_remote_requests(temp_requests)
        local_batch._save_remote_state(message_batch.model_dump())
        return message_batch.id

    def cancel_batch(self, local_batch: Batch) -> None:
        """Cancel the batch in Anthropic."""
        message_batch = self.client.messages.batches.cancel(local_batch.remote_id)
        local_batch._save_remote_state(message_batch)

    def sync_batch(self, local_batch: Batch) -> None:
        """Sync the batch in Anthropic."""
        message_batch = self.client.messages.batches.retrieve(local_batch.remote_id)
        local_batch._save_remote_state(message_batch.model_dump())

    def download_batch_results(self, local_batch: Batch) -> None:
        """Download and save batch results from Anthropic.
        
        The results() method returns a JSONLDecoder that yields MessageBatchIndividualResponse
        objects for each request in the batch.
        """
        results_iterator = self.client.messages.batches.results(local_batch.remote_id)
        batch_results = []
        
        for result in results_iterator:
            batch_results.append(result)
            
        local_batch._save_remote_results(batch_results)

    def convert_batch_status(self, provider_state: Dict[str, Any]) -> LocalBatchStatus:
        """Convert our tracking state to LocalBatchStatus."""
        if provider_state["processing_status"] == "in_progress":
            return LocalBatchStatus.IN_PROGRESS
        elif provider_state["processing_status"] == "ended":
            if provider_state["request_counts"]["canceled"] == 0:
                return LocalBatchStatus.COMPLETED
            else:
                return LocalBatchStatus.CANCELLED
        elif provider_state["processing_status"] == "canceling":
            return LocalBatchStatus.CANCELLED
        else:
            return LocalBatchStatus.FAILED

    def convert_batch_result(self, provider_result: Dict[str, Any]) -> Result:
        """Convert Anthropic result format to Result model."""
        result = MessageBatchIndividualResponse(**provider_result)
        if result.result.type == "succeeded":
            temp_m = result.result.message.content
            finish_reason = result.result.message.stop_reason
            choices = [Choice(message=AssistantMessage(content=content_provider.text),
                               finish_reason=finish_reason,
                               index=index)
                             for index, content_provider in enumerate(temp_m)]

            return Result(
                custom_id=result.custom_id,
                choices=choices,
                model=result.result.message.model,
                usage=result.result.message.usage.model_dump()
            )
        elif result.result.type == "errored":
            return Result(
                custom_id=result.custom_id,
                choices=[],
                error=str(result.result.error.model_dump())
            )
