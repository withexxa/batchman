import os
import batchman
from batchman import Request, UserMessage, ProviderConfig

batch = batchman.create_batch(
    "stories-generation",
    unique_id="1234567890",
    provider="openai",
    provider_config=ProviderConfig(api_key=os.getenv("OPENAI_API_KEY")),
)

jobs = ["an astronaut", "a doctor", "a firefighter", "a teacher", "a chef", "a farmer", "a pilot", "a police officer",
        "a baker", "a scientist", "a writer", "a musician", "an actor", "an artist", "an engineer", "a lawyer", "an architect", "a designer", "a manager"]

batch.add_requests(
    [Request([UserMessage(f"Write a short story about a child dreaming of being {job}.")]) for job in jobs]
)

batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children."
                  "The goal of the stories are to motivate them to pursue their dreams",
    model="gpt-4o-mini",
    temperature=0.5,
)

# Upload the batch
uploaded_batch = batch.upload()
print(uploaded_batch.status)