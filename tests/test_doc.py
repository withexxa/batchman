import pytest
from batchman import load_batch, create_batch, list_batches, sync_batches, delete_batch
from batchman import Batcher

def test_doc_similarity():
    assert load_batch.__doc__ == Batcher.load_batch.__doc__
    assert create_batch.__doc__ == Batcher.create_batch.__doc__
    assert list_batches.__doc__ == Batcher.list_batches.__doc__
    assert sync_batches.__doc__ == Batcher.sync_batches.__doc__
    assert delete_batch.__doc__ == Batcher.delete_batch.__doc__