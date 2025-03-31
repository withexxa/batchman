import os
import batchman
from batchman import Request, UserMessage, ProviderConfig

batch = batchman.create_batch(
    "stories-generation",
    provider="exxa",
)

jobs = ["an astronaut", "a doctor", "a firefighter", "a teacher", "a chef", "a farmer", "a pilot", "a police officer", "a baker", "a scientist", "a writer",
         "a musician", "an actor", "an artist", "an engineer", "a lawyer", "a architect", "a designer", "a manager"]

batch.add_requests(
    [Request([UserMessage(f"Write a short story about a child dreaming of being {job}.")]) for job in jobs]
)

# Set the request parameters for the batch. These will be set for all the requests in the batch.
batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children. The goal of the stories are to motivate them to pursue their dreams.",
    temperature=0.5,
)

# Upload the batch for each model
for model in ["llama-3.3-70b-instruct-fp16", "llama-3.1-8b-instruct-fp16"]:
    batch.override_request_params(
        model=model,
    )
    batch.upload()
    # An uploaded batch is not editable, so we need to copy it (but we keep the same provider)
    batch = batch.copy(keep_provider=True)
