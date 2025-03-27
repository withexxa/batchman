import pytest
from pathlib import Path

from batchman import Batcher
from batchman.models import LocalBatchStatus, Request, UserMessage
from batchman.models.batch import Batch


@pytest.fixture
def temp_batches_dir(tmp_path):
    return tmp_path / "test_batches"


@pytest.fixture
def batcher_test(temp_batches_dir) -> Batcher:
    return Batcher(batches_dir=temp_batches_dir)


def test_create_batcher(temp_batches_dir):
    batcher = Batcher(batches_dir=temp_batches_dir)
    assert batcher.batches_dir == temp_batches_dir
    assert batcher.batches_dir.exists()


def test_create_and_fill_batch(batcher_test: Batcher):
    batch = batcher_test.create_batch(name="test-batch", provider="exxa")

    batch.add_requests(
        [
            Request(
                [UserMessage(content="Test prompt 1")],
                temperature=0.8,
            ),
            Request(
                messages=[UserMessage(content="Test prompt 2")],
                temperature=0.9,
            ),
            Request(
                UserMessage(content="Test prompt 3"),
                temperature=0.7,
            ),
        ]
    )

    assert batch.params.name == "test-batch"
    assert batch.status == LocalBatchStatus.INITIALIZING
    assert batch.directory.exists()

    reqs = batch.requests

    assert len(reqs) == 3
    assert reqs[0].messages[0].content == "Test prompt 1"
    assert reqs[1].messages[0].content == "Test prompt 2"
    assert reqs[2].messages[0].content == "Test prompt 3"


def test_list_batches(batcher_test: Batcher):
    batch = batcher_test.create_batch(name="test-batch")

    batch.add_requests(
        [
            Request(
                messages=[UserMessage(content="Test prompt 1")],
                temperature=0.8,
            ),
            Request(
                messages=[UserMessage(content="Test prompt 2")],
                temperature=0.9,
            ),
        ]
    )

    editable_batches, uploaded_batches, downloaded_batches, errors = batcher_test.list_batches()
    assert len(editable_batches) == 1
    assert len(uploaded_batches) == 0
    assert len(downloaded_batches) == 0
    assert len(errors) == 0
