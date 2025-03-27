from pydantic import BaseModel
from typing import Dict, List, Optional, Union
from .dataclasses import Choice


class Result(BaseModel):
    custom_id: str
    choices: List[Choice]
    usage: Optional[Dict[str, Union[int, Dict[str, int]]]] = None
    error: Optional[str] = None
