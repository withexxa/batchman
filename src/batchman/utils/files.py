import json
from pathlib import Path
from typing import Any, Dict, List, TextIO, Union
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

DictOrModel = Union[Dict[str, Any], BaseModel]


def fwrite(f: TextIO, data: DictOrModel, end: str = "") -> None:
    if isinstance(data, BaseModel):
        data = data.model_dump()
    f.write(json.dumps(to_jsonable_python(data)) + end)


def read_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            txt = f.read()
            data = json.loads(txt)
    except FileNotFoundError:
        raise FileNotFoundError(f"File {path} not found")
    except Exception as e:
        raise ValueError(f"Could not read JSON file {path}: {e}")
    return data


def write_json(path: Path, data: DictOrModel) -> None:
    with open(path, "w") as f:
        fwrite(f, data)


def upsert_json(path: Path, data: DictOrModel) -> None:
    # If the file doesn't exist, create it
    if not path.exists():
        write_json(path, data)
        return

    # Read the file
    file_data = read_json(path)

    # Update the file
    file_data.update(to_jsonable_python(data))

    # Write the file
    write_json(path, file_data)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        non_empty_lines = (line for line in f if line.strip())
        return [json.loads(line) for line in non_empty_lines]


def write_jsonl(path: Path, data: Union[DictOrModel, List[DictOrModel], str]) -> None:
    with open(path, "w") as f:
        if isinstance(data, str):
            f.write(data + "\n")
        elif isinstance(data, dict):
            fwrite(f, data, end="\n")
        elif isinstance(data, list):
            for item in data:
                fwrite(f, item, end="\n")


def append_jsonl(path: Path, data: Union[DictOrModel, List[DictOrModel], str]) -> None:
    with open(path, "a") as f:
        if isinstance(data, str):
            f.write(data + "\n")
        elif isinstance(data, (dict, BaseModel)):
            fwrite(f, data, end="\n")
        elif isinstance(data, list):
            for item in data:
                fwrite(f, item, end="\n")
        else:
            raise ValueError(f"Invalid data type: {type(data)}")
