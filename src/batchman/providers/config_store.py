import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from ..models.provider_config import ProviderConfig


class ConfigStore:
    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            # Create empty file
            self.store_path.touch()

    def _read_store(self) -> Dict[str, Dict[str, Any]]:
        store = {}
        if self.store_path.exists() and self.store_path.stat().st_size > 0:
            with open(self.store_path, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    store[entry["hash"]] = entry["config"]
        return store

    def _append_entry(self, config_hash: str, config: Dict[str, Any]) -> None:
        with open(self.store_path, "a") as f:
            entry = {"hash": config_hash, "config": config}
            f.write(json.dumps(entry) + "\n")

    def _rewrite_store(self, store: Dict[str, Dict[str, Any]]) -> None:
        with open(self.store_path, "w") as f:
            for config_hash, config in store.items():
                entry = {"hash": config_hash, "config": config}
                f.write(json.dumps(entry) + "\n")

    def _compute_hash(self, config: Dict[str, Any]) -> str:
        # Sort the dictionary to ensure consistent hashing
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def store(self, config: ProviderConfig) -> str:
        """Store config and return its hash"""
        config_hash = self._compute_hash(config.model_dump(exclude_none=True))
        store = self._read_store()

        # If this config is already stored (with this hash), no need to append
        if config_hash not in store:
            self._append_entry(config_hash, config.model_dump(exclude_none=True))

        return config_hash

    def get(self, config_hash: str) -> Optional[ProviderConfig]:
        """Retrieve config by its hash"""
        store = self._read_store()
        config = store.get(config_hash)
        if config is None:
            return None
        return ProviderConfig(**config)

    def remove(self, config_hash: str) -> None:
        """Remove config by its hash"""
        store = self._read_store()
        if config_hash in store:
            del store[config_hash]
            self._rewrite_store(store)
