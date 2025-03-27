from pydantic.dataclasses import dataclass
from typing import List, Union
from .enums import MessageRole


@dataclass
class ImageContent:
    url: str
    type: str = "image"


@dataclass
class TextContent:
    content: str
    type: str = "text"


@dataclass
class Message:
    content: Union[str, List[Union[ImageContent, TextContent]]]
    role: MessageRole


@dataclass
class UserMessage(Message):
    role: MessageRole = MessageRole.USER


class SystemMessage(Message):
    role: MessageRole = MessageRole.SYSTEM


@dataclass
class AssistantMessage(Message):
    role: MessageRole = MessageRole.ASSISTANT


@dataclass
class Choice:
    message: AssistantMessage
    finish_reason: str
    index: int
