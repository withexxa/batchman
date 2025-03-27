import pytest
from pathlib import Path
from batchman.providers.config_store import ConfigStore
from batchman.providers.base import ProviderConfig

@pytest.fixture
def temp_store_path(tmp_path):
    return tmp_path / "provider_configs.jsonl"


@pytest.fixture
def config_store(temp_store_path):
    return ConfigStore(temp_store_path)


def test_store_and_retrieve_config(config_store):
    config = ProviderConfig(api_key="test-key", base_url="https://api.test.com")
    config_hash = config_store.store(config)

    # Check that we can retrieve the config
    retrieved_config = config_store.get(config_hash)
    assert retrieved_config == config

    # Store the same config again - should return same hash
    same_hash = config_store.store(config)
    assert same_hash == config_hash


def test_store_multiple_configs(config_store):
    config1 = ProviderConfig(api_key="key1", base_url="https://api1.test.com")
    config2 = ProviderConfig(api_key="key2", base_url="https://api2.test.com")

    hash1 = config_store.store(config1)
    hash2 = config_store.store(config2)

    # Hashes should be different
    assert hash1 != hash2

    # Both configs should be retrievable
    assert config_store.get(hash1) == config1
    assert config_store.get(hash2) == config2


def test_remove_config(config_store):
    config = ProviderConfig(api_key="test-key")
    config_hash = config_store.store(config)

    # Config should exist
    assert config_store.get(config_hash) == config

    # Remove the config
    config_store.remove(config_hash)

    # Config should no longer exist
    assert config_store.get(config_hash) is None


def test_hash_consistency(config_store):
    config = ProviderConfig(kwargs={"b": 2, "a": 1})  # Deliberately unordered
    config_ordered = ProviderConfig(kwargs={"a": 1, "b": 2})  # Same config, different order

    hash1 = config_store.store(config)
    hash2 = config_store.store(config_ordered)

    # Hashes should be the same regardless of key order
    assert hash1 == hash2


def test_persistence(temp_store_path):
    # Create first store instance and add config
    config_store_1 = ConfigStore(temp_store_path)
    config = ProviderConfig(api_key="test-key")
    config_hash = config_store_1.store(config)

    # Create new store instance pointing to same file
    config_store_2 = ConfigStore(temp_store_path)

    # Should be able to retrieve config from new instance
    assert config_store_2.get(config_hash) == config


def test_nonexistent_hash(config_store):
    assert config_store.get("nonexistent") is None


def test_empty_config(config_store):
    config = ProviderConfig()
    config_hash = config_store.store(config)
    assert config_store.get(config_hash) == config

    config = ProviderConfig(
        api_key="test-key",
        kwargs={"timeout": 30, "retries": 3},
        options=["opt1", "opt2"],
    )
    config_hash = config_store.store(config)
    assert config_store.get(config_hash) == config
