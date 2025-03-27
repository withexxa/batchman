import os
import time
import requests
from batchman import Request, UserMessage, ProviderConfig, Batcher, LocalBatchStatus

# batcher = Batcher(batches_dir="batches_test")

test_batcher = Batcher(batches_dir="batches_test_temp")

batch = test_batcher.create_batch(
    "stories-generation",
    provider="exxa",
    provider_config=ProviderConfig(api_key=os.getenv("EXXA_API_KEY"), url="https://api.dev.withexxa.com/v1"),
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
    model="llama-3.1-8b-instruct-fp16",
    temperature=0.5,
)

uploaded_batch = batch.upload()
print(uploaded_batch.status)

time.sleep(1)

client = requests.Session()
headers = {"X-API-Key": os.getenv("EXXA_API_KEY"), "Content-Type": "application/json"}


exxa_batch = client.get(f"https://api.dev.withexxa.com/v1/batches/{uploaded_batch.remote_id}", headers=headers)

assert exxa_batch.json()["status"] == "registered"

uploaded_batch.sync()
assert uploaded_batch.status == LocalBatchStatus.REGISTERED

uploaded_batch.cancel()

time.sleep(1)

exxa_batch = client.get(f"https://api.dev.withexxa.com/v1/batches/{uploaded_batch.remote_id}", headers=headers)

assert exxa_batch.json()["status"] == "cancelled"

uploaded_batch.sync()

assert uploaded_batch.status == LocalBatchStatus.CANCELLED

test_batcher._rm_batch_dir(im_sure_to_delete_all_batches=True)

print("Test passed, no assertions failed")