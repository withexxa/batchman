from .registry import ProviderRegistry
from pathlib import Path
from batchman.utils.logging import logger


def discover_providers():
    """Discover provider modules in the providers directory."""
    providers_dir = Path(__file__).parent
    for file in providers_dir.glob("*.py"):
        if file.stem in ["__init__", "base", "registry", "config_store"]:
            continue

        module_name = f"batchman.providers.{file.stem}"
        try:
            ProviderRegistry.try_register_provider(module_name)
        except Exception as e:
            logger.warning(f"Failed to load provider from {file}: {e}")


discover_providers()
