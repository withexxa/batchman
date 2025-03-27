# All theses tests require the auto_tests_manual_init.py to be run first

import pytest
import shutil
from batchman import Batcher, LocalBatchStatus
from batchman.models import Result
from typing import List
import time
import os


@pytest.fixture(scope="session", autouse=True)
def persistent_batcher() -> Batcher:
    shutil.copytree("batches_persistent_test", "batches_persistent_test_copy")
    persistent_batcher = Batcher("batches_persistent_test_copy")
    yield persistent_batcher
    shutil.rmtree("batches_persistent_test_copy")

def checking_result_correctness(res: List[Result]):
    for result in res:
        assert result.choices is not None
        assert result.choices[0].message.content is not None
        assert type(result.choices[0].message.content) == str
        assert result.choices[0].message.content != ""
        assert result.choices[0].message.content.strip() != ""
        assert result.usage is not None
        # TODO: fix this, right now it's not unified and Anthropic doesn't work the same way as OpenAI
        # try:
        #     assert result.usage["completion_tokens"] > 0, f"usage error: {result.usage}"
        #     assert result.usage["prompt_tokens"] > 0, f"usage error: {result.usage}"
        # except KeyError as e:
        #     print(f"usage error: {result.usage}")
        #     raise e
        assert result.custom_id is not None
        assert result.custom_id != ""
        assert result.error is None


def test_env_variables():
    # test required env variables
    assert os.getenv("OPENAI_API_KEY") is not None
    assert os.getenv("ANTHROPIC_API_KEY") is not None
    assert os.getenv("EXXA_API_KEY") is not None


def test_load_batch_openai(persistent_batcher: Batcher):
    batch = persistent_batcher.load_batch(unique_id="1111111111", name="stories-generation-openai")
    assert batch is not None
    batch.sync()
    assert batch.status == LocalBatchStatus.COMPLETED
    downloaded_batch = batch.download()
    res = downloaded_batch.get_results()
    assert len(res) == 3
    batch2 = persistent_batcher.load_batch(unique_id="1111111111")
    assert batch2.status == batch.status
    assert batch2.get_results() == res
    assert batch2.metadata == batch.metadata == {"batcher-user-metadata": "openai"}
    checking_result_correctness(res)


def test_load_failed_openai(persistent_batcher: Batcher):
    batch = persistent_batcher.load_batch(unique_id="5555555555", name="openai-fail-params")
    assert batch is not None
    batch.sync()
    assert batch.status == LocalBatchStatus.COMPLETED
    batch2 = persistent_batcher.load_batch(unique_id="5555555555")
    assert batch2.status == batch.status
    assert batch2.metadata == batch.metadata == {"batcher-user-metadata": "openai"}
    downloaded_batch = batch2.download()
    res = downloaded_batch.get_results()
    assert len(res) == 4
    assert res[0].error is None
    assert res[1].error is None
    assert res[2].error is None
    assert res[3].error is not None


def test_load_batch_anthropic(persistent_batcher: Batcher):
    batch = persistent_batcher.load_batch(unique_id="2222222222", name="stories-generation-anthropic")
    assert batch is not None
    batch.sync()
    assert batch.status == LocalBatchStatus.COMPLETED
    downloaded_batch = batch.download()
    res = downloaded_batch.get_results()
    assert len(res) == 3
    batch2 = persistent_batcher.load_batch(unique_id="2222222222")
    assert batch2.status == batch.status
    assert batch2.get_results() == res
    assert batch2.metadata == batch.metadata == {"batcher-user-metadata": "anthropic"}
    checking_result_correctness(res)

def test_load_failed_anthropic(persistent_batcher: Batcher):
    batch = persistent_batcher.load_batch(unique_id="4444444444", name="anthropic-fail-params")
    assert batch is not None
    batch.sync()
    assert batch.status == LocalBatchStatus.COMPLETED
    downloaded_batch = batch.download()
    res = downloaded_batch.get_results()
    assert len(res) == 4
    assert downloaded_batch.metadata == {"batcher-user-metadata": "anthropic"}
    assert res[0].error is None
    assert res[1].error is None
    assert res[2].error is None
    print(res[3].error)
    assert res[3].error is not None


def test_load_batch_exxa(persistent_batcher: Batcher):
    batch = persistent_batcher.load_batch(unique_id="3333333333", name="stories-generation-exxa")
    assert batch is not None
    batch.sync()
    assert batch.status == LocalBatchStatus.COMPLETED
    downloaded_batch = batch.download()
    res = downloaded_batch.get_results()
    assert len(res) == 3
    assert downloaded_batch.metadata == {"batcher-user-metadata": "exxa"}
    checking_result_correctness(res)
