import batchman
from batchman import DownloadedBatch

# Load the batch you want to read
batch = batchman.load_batch(unique_id="your-unique-id", name="your-batch-name")

# This works only if the batch has been uploaded, completed and then downloaded, check stories_generation_load.py for an example
assert isinstance(batch, DownloadedBatch)

for result in batch.get_results():
    print(result.choices[0].message.content)