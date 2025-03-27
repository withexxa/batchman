import os
import time
import batchman
from batchman import Request, UserMessage, LocalBatchStatus, UploadedBatch, DownloadedBatch

# batchman = Batcher(batches_dir="batches_test")

try:
    batch = batchman.create_batch(
        "stories-generation",
        provider="anthropic",
        unique_id="1212121212",
    )


    jobs_str = "an astronaut|a doctor"
    jobs = jobs_str.split("|")

    batch.add_requests(
        [
            Request(
                [
                    UserMessage(
                        f"Write a short story about a child dreaming of being {job}."
                    ),
                ]
            )
            for job in jobs
        ]
    )

    batch.override_request_params(
        system_prompt="You are a creative writer who writes short stories for children. The goal of the stories are to motivate them to pursue their dreams and to make them believe that they can achieve anything they want.",
        model="claude-3-5-haiku-latest",
        temperature=0.5,
        max_tokens=1000,
    )

    uploaded_batch = batch.upload()
    print(uploaded_batch.status)
except FileExistsError as e:
    # Batch already exists, error expected
    print("Batch already exists, error expected")

time.sleep(1)

loaded_batch = batchman.load_batch(
    "1212121212",
    "stories-generation",
)

if isinstance(loaded_batch, UploadedBatch):
    print("Uploaded batch")
    loaded_batch.sync()
    if loaded_batch.status == LocalBatchStatus.COMPLETED:
        print("Downloading batch")
        loaded_batch = loaded_batch.download()

if isinstance(loaded_batch, DownloadedBatch):
    print("Downloaded batch, showing results")
    res = loaded_batch.get_results()
    print(res)
