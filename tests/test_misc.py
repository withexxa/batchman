import os
import shutil
import pytest
from batchman import Request, UserMessage, ProviderConfig, Batcher
from batchman.providers.registry import ProviderRegistry


@pytest.fixture(autouse=True, scope="session")
def temp_batcher():
    shutil.rmtree("batches_pytest_temp", ignore_errors=True)
    batcher = Batcher(batches_dir="batches_pytest_temp")
    yield batcher
    batcher._rm_batch_dir(im_sure_to_delete_all_batches=True)

def test_late_provider(temp_batcher : Batcher):
    batch = temp_batcher.create_batch(
        "stories-generation",
        unique_id="1234567890",
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
        model="gpt-4o-mini",
        temperature=0.5,
    )

    batch.set_provider(
        provider="openai",
        provider_config=ProviderConfig(api_key=os.getenv("OPENAI_API_KEY")),
    )

    test_batch_copy = batch.copy("test_batch")

    test_batch_copy.override_request_params(model="claude-3-5-sonnet-latest", max_tokens=1000)
    test_batch_copy.set_provider(
        provider="anthropic",
        provider_config=ProviderConfig(api_key=os.getenv("ANTHROPIC_API_KEY")),
    )

def test_upload_not_set_provider(temp_batcher: Batcher):
    batch = temp_batcher.create_batch("failing")
    batch.add_requests([Request([UserMessage("Write a short story about a child dreaming of being a doctor.")])])
    with pytest.raises(ValueError):
        batch.upload()
