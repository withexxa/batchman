import os
import batchman
from batchman import ProviderConfig, UploadedBatch, DownloadedBatch, LocalBatchStatus

try:
    batch = batchman.create_batch(
        "stories-generation",
        unique_id="1234567890",
        provider="openai",
        provider_config=ProviderConfig(api_key=os.getenv("OPENAI_API_KEY")),
    )
except FileExistsError as e:
    # Batch already exists, error expected if the script is run multiple times
    print("Batch already exists, error expected")

# Load the batch
loaded_batch = batchman.load_batch(
    "1234567890",
    "stories-generation",
)

# If the batch has been uploaded, check the status
if isinstance(loaded_batch, UploadedBatch):
    # Sync the batch to get the latest status
    loaded_batch.sync()
    # If the batch is completed, download the results
    if loaded_batch.status == LocalBatchStatus.COMPLETED:
        print("Downloading batch")
        loaded_batch = loaded_batch.download()

if isinstance(loaded_batch, DownloadedBatch):
    print("Downloaded batch, showing results")
    res = loaded_batch.get_results()
    print(res)
