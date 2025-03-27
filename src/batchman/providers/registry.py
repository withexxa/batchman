from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from .config_store import ConfigStore
from ..utils.logging import logger
import importlib
from batchman.models.provider_config import ProviderConfig

if TYPE_CHECKING:
    from .base import Provider


class ProviderRegistry:
    _providers: Dict[str, Type["Provider"]] = {}

    # Config store in the current directory
    _config_store = ConfigStore(Path.cwd() / "providers_configs.jsonl")

    @classmethod
    def register(cls, provider_cls: Type["Provider"]) -> None:
        cls._providers[provider_cls.name] = provider_cls

    @classmethod
    def try_register_provider(cls, module_name: str) -> None:
        """
        Attempt to import and register a provider. Silently skip if dependencies are missing.
        Args:
            module_name: The module name (e.g., 'batchman.providers.openai')
        """
        try:
            module = importlib.import_module(module_name)
            # Find the first class that ends with 'Provider', but avoid importing the base Provider class itself
            provider_class_name = None
            for name, obj in module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and name.endswith("Provider")
                    and not name.startswith("Provider")
                ):
                    provider_class_name = name
                    break
            if provider_class_name is None:
                raise ValueError(f"No provider class found in module {module_name}")
            provider_cls = getattr(module, provider_class_name)
            cls.register(provider_cls)
        except ImportError as e:
            logger.warning(
                f"Provider in {module_name} not available - missing dependencies: {e}"
            )
        except Exception as e:
            logger.warning(f"Failed to register {module_name}: {str(e)}")

    @classmethod
    def list(cls) -> List[Type["Provider"]]:
        return list(cls._providers.values())

    @classmethod
    def get(cls, provider_name: str) -> Optional[Type["Provider"]]:
        """Get the provider class for a given provider name."""
        return cls._providers.get(provider_name, None)

    @classmethod
    def is_registered(cls, provider_name: str) -> bool:
        return provider_name in cls._providers

    @classmethod
    def get_stored_config(cls, config_hash: str) -> Optional[ProviderConfig]:
        return cls._config_store.get(config_hash)

    @classmethod
    def store_config(cls, config: ProviderConfig) -> str:
        return cls._config_store.store(config)

    @classmethod
    def get_default_config_hash(cls, provider_name: str) -> str:
        provider_class = cls._providers.get(provider_name, None)
        if provider_class is None:
            raise ValueError(f"Provider {provider_name} not found")
        #creating a provider instance without config to get default config
        provider = provider_class()
        provider_config = provider.config
        config_hash = cls.store_config(provider_config)
        return config_hash
