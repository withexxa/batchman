import os
import batchman
from batchman import Request, UserMessage, ProviderConfig

batch = batchman.create_batch(
    "stories-generation",
    provider="exxa",
    provider_config=ProviderConfig(
        api_key=os.getenv("EXXA_API_KEY"),
        url=os.getenv("EXXA_API_URL"),
    ),
)

jobs_str = "an astronaut|a doctor|a firefighter|a teacher|a chef|a farmer|a pilot|a police officer|a baker|a scientist|a writer|a musician|a actor|a artist|a engineer|a lawyer|a architect|a designer|a manager"
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

batch.upload()
