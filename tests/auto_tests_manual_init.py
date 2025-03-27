# This file must be run manually: it requires valid API keys for OpenAI, Exxa and Anthropic,
# and upload different batches to each provider. Then once theses batches are completed
# on each provider, they can be used in automatic tests.

import os
from batchman import Request, UserMessage, ProviderConfig, Batcher

persistent_test_batches_dir = "batches_persistent_test"

persistent_batcher = Batcher(batches_dir=persistent_test_batches_dir)

jobs_list = ["an astronaut", "a doctor", "a firefighter"]
requests = [
    Request(
            [
                UserMessage(
                    f"Write a short story about a child dreaming of being {job}."
                ),
            ]
        )
    for job in jobs_list
]

# test required env variables

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY is not set")
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY is not set")
if not os.getenv("EXXA_API_KEY"):
    raise ValueError("EXXA_API_KEY is not set")

# OpenAI

openai_batch = persistent_batcher.create_batch(
    "stories-generation-openai",
    unique_id="1111111111",
    provider="openai",
    provider_config=ProviderConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
)
openai_batch.add_requests(requests)
openai_batch.add_metadata({"batcher-user-metadata": "openai"})
openai_batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children. The goal of the stories are to motivate them to pursue their dreams and to make them believe that they can achieve anything they want.",
    model="gpt-4o-mini",
)
openai_batch.upload()
print("uploaded openai batch")

openai_copy = openai_batch.copy(new_name="openai-fail-params", new_unique_id="5555555555", keep_provider=True)
openai_copy.add_requests(
    Request(messages=[
                UserMessage(
                    f"Write a short story about a child dreaming of being an IT developer."
                ),],
                frequency_penalty=1.0,
                presence_penalty=1.0,
                temperature=-100.0,
        )
)
openai_copy.upload()
print("uploaded openai batch with (probably?) unsupported params")

# Anthropic

anthropic_batch = persistent_batcher.create_batch(
    "stories-generation-anthropic",
    unique_id="2222222222",
    provider="anthropic",
    provider_config=ProviderConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
)
anthropic_batch.add_requests(requests)
anthropic_batch.add_metadata({"batcher-user-metadata": "anthropic"})
anthropic_batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children. The goal of the stories are to motivate them to pursue their dreams and to make them believe that they can achieve anything they want.",
    model="claude-3-5-sonnet-20240620",
    max_tokens=3000,
)
anthropic_batch.upload()
print("uploaded anthropic batch")

anthropic_copy = anthropic_batch.copy(new_name="anthropic-fail-params", new_unique_id="4444444444", keep_provider=True)
anthropic_copy.add_requests(
    Request(messages=[
                UserMessage(
                    f"Write a short story about a child dreaming of being an IT developer."
                ),],
                frequency_penalty=1.0,
                presence_penalty=1.0,
                temperature=-10.0,
        )
)
anthropic_copy.upload()
print("uploaded anthropic batch with unsupported params")

# Exxa (using dev env)

exxa_batch = persistent_batcher.create_batch(
    "stories-generation-exxa",
    unique_id="3333333333",
    provider="exxa",
    provider_config=ProviderConfig(
        api_key=os.getenv("EXXA_API_KEY"),
        url="https://api.dev.withexxa.com/v1",
    ),
)

exxa_batch.add_requests(requests)
exxa_batch.add_metadata({"batcher-user-metadata": "exxa"})
exxa_batch.override_request_params(
    system_prompt="You are a creative writer who writes short stories for children. The goal of the stories are to motivate them to pursue their dreams and to make them believe that they can achieve anything they want.",
    model="llama-3.1-8b-instruct-fp16",
)

exxa_batch.upload()
print("uploaded exxa batch")
