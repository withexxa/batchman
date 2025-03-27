from typing import List, Any, Optional, Dict, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import to_jsonable_python

from batchman.models.enums import MessageRole
from .dataclasses import Message


class Request(BaseModel):
    """
    A request to be sent to a provider.

    Can be given the system prompt through the messages, it will be automatically removed from the messages
    and added to the system_prompt field.

    Warning: Does not support multiple system messages, will raise a ValidationError if given.
    """
    messages: List[Message]
    custom_id: str = Field(default_factory=lambda: "request-" + str(uuid.uuid4()))
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    n: Optional[int] = None

    def __init__(self, messages: List[Message], **data: Any):
        if isinstance(messages, Message):
            messages = [messages]

        thread_messages = []
        for message in messages:
            msg = Message(**to_jsonable_python(message))

            if msg.role == MessageRole.SYSTEM:
                if data.get("system_prompt"):
                    raise ValidationError("Cannot have multiple system messages")
                data["system_prompt"] = msg.content
            else:
                thread_messages.append(msg)

        data["messages"] = thread_messages

        super().__init__(**data)

    def __str__(self) -> str:
        return (
            f"Request({', '.join([f'{k}={repr(v)}' for k, v in self.dict().items()])})"
        )
