import os
import time
import openai
from openai import OpenAI
from batchman import Request, UserMessage, Batcher, LocalBatchStatus

# batcher = Batcher(batches_dir="batches_test")

test_batcher = Batcher(batches_dir="batches_test_temp")

batch = test_batcher.create_batch(
    "stories-generation",
    provider="openai",
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
    model="gpt-4o-mini",
    temperature=0.5,
)

uploaded_batch = batch.upload()
print(uploaded_batch.status)

time.sleep(1)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

openai_batch = client.batches.retrieve(uploaded_batch.remote_id)

assert openai_batch.status == "in_progress" or openai_batch.status == "validating"

uploaded_batch.sync()
assert uploaded_batch.status == LocalBatchStatus.VALIDATING or uploaded_batch.status == LocalBatchStatus.REGISTERED or uploaded_batch.status == LocalBatchStatus.IN_PROGRESS

uploaded_batch.cancel()

time.sleep(1)

openai_batch = client.batches.retrieve(uploaded_batch.remote_id)
assert openai_batch.status == "cancelling" or openai_batch.status == "cancelled"

uploaded_batch.sync()

assert uploaded_batch.status == LocalBatchStatus.CANCELLED

test_batcher._rm_batch_dir(im_sure_to_delete_all_batches=True)

print("Test passed, no assertions failed")