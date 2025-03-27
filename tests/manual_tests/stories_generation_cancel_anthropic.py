import os
import time
import anthropic
from batchman import Request, UserMessage, ProviderConfig, Batcher, LocalBatchStatus

# batcher = Batcher(batches_dir="batches_test")

test_batcher = Batcher(batches_dir="batches_test_temp")

batch = test_batcher.create_batch(
    "stories-generation",
    provider="anthropic",
    provider_config=ProviderConfig(api_key=os.getenv("ANTHROPIC_API_KEY")),
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

time.sleep(1)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

anthropic_batch = client.messages.batches.retrieve(uploaded_batch.remote_id)

assert anthropic_batch.processing_status == "in_progress"

uploaded_batch.sync()
assert uploaded_batch.status == LocalBatchStatus.VALIDATING or uploaded_batch.status == LocalBatchStatus.REGISTERED or uploaded_batch.status == LocalBatchStatus.IN_PROGRESS

uploaded_batch.cancel()

time.sleep(1)

anthropic_batch = client.messages.batches.retrieve(uploaded_batch.remote_id)
assert anthropic_batch.processing_status == "canceling" or anthropic_batch.processing_status == "ended"

uploaded_batch.sync()

assert uploaded_batch.status == LocalBatchStatus.CANCELLED

test_batcher._rm_batch_dir(im_sure_to_delete_all_batches=True)

print("Test passed, no assertions failed")