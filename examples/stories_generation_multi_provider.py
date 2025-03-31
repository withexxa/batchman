import os
import batchman
from batchman import Request, UserMessage, ProviderConfig

batch = batchman.create_batch(
    "stories-generation",
)

jobs = ["an astronaut", "a doctor", "a firefighter", "a teacher", "a chef", "a farmer", "a pilot", "a police officer", "a baker", "a scientist", "a writer",
         "a musician", "an actor", "an artist", "an engineer", "a lawyer", "a architect", "a designer", "a manager"]

batch.add_requests(
    [Request([UserMessage(f"Write a short story about a child dreaming of being {job}.")]) for job in jobs]
)

# Set the request parameters for the batch. These will be set for all the requests in the batch, and would erase any request parameters already set for the requests.
batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children."
                  "The goal of the stories are to motivate them to pursue their dreams",
    model="llama-3.1-8b-instruct-fp16",
    temperature=0.5,
)

# Set the provider to exxa and upload the batch
batch.set_provider(
    provider="exxa",
    provider_config=ProviderConfig(
        api_key=os.getenv("EXXA_API_KEY"),
        url=os.getenv("EXXA_API_URL"),
    ),
)
batch.upload()


# Set the provider to openai and upload the batch
# An uploaded batch is not editable, so we need to copy it
batch_copy = batch.copy()
# Set a model compatible with the provider
batch_copy.override_request_params(
    model="gpt-4o-mini",
)
# If not specified, the API key will be taken from the environment variable OPENAI_API_KEY
batch_copy.set_provider(provider="openai")
batch_copy.upload()


# Same for anthropic
batch_copy = batch.copy()
# Set a model compatible with the provider
batch_copy.override_request_params(
    model="claude-3-5-haiku-latest",
)
batch_copy.set_provider(provider="anthropic")
batch_copy.upload()
