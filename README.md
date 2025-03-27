# Batchman - Batch LLM requests

A flexible Python library for managing batches of requests to LLM inference providers.

## Features

- Use batch providers through a unified API
- Validate requests before uploading
- Keep track of uploaded batches and their status
- [TODO] Visualize batch requests and results
- [TODO] Support streaming results for dev mode

## Installation

### From PyPI

```bash
pip install batchman[all]
```

If you don't want to install all the providers, you can install only the ones you need, and install
the minimum dependencies with

```bash
pip install batchman
```

### For Development

```bash
git clone https://github.com/yourusername/batchman.git
cd batchman
uv pip install -e .[dev,all]
```

to build the pypi package, run

```bash
uv build
```

to publish to testpypi, run

```bash
uv publish --index testpypi --username __token__ --password $PYPITEST_TOKEN
```

Downloading from the test index:

```bash
pip install --verbose -i https://test.pypi.org/simple/  --extra-index-url https://pypi.org/simple/ batchman[all]
```

### Building the documentation

```bash
tox -e docs
```

## Quickstart

### Creating a batch

```python
import batchman
from batchman import Request, UserMessage

# Initialize a new batch
batch = batchman.create_batch("my batch")

# Example: Generate stories for different professions
jobs = [
    "an astronaut", "a doctor", "a firefighter", "a teacher",
    "a chef", "a farmer", "a pilot", "a scientist"
]

# Add requests to the batch
batch.add_requests([
    Request([
        UserMessage(f"Write a short story about a child dreaming of being {job}.")
    ])
    for job in jobs
])

# Configure batch parameters
batch.override_request_params(
    system_prompt=(
        "You are a creative writer who writes short stories for children. "
        "The goal of the stories are to motivate them to pursue their dreams "
        "and to make them believe that they can achieve anything they want."
    ),
    model="llama-3.1-70b-instruct-fp16",
    temperature=0.5,
)

# Set the provider (uses EXXA_API_KEY environment variable by default)
batch.set_provider(provider="exxa")

# Upload the batch
batch.upload()
```

### Managing Batches

#### Sync batches
Use the `batchman sync` command to sync all batches. This will fetch the status of all non-completed batches and download the results when the batch is completed.

```bash
# Sync all batches
batchman sync

# Sync batches in a specific directory
batchman --dir path/to/batches sync
```

#### List batches

```bash
# List all batches
batchman list

# List batches in a specific directory
batchman --dir path/to/batches list
```

### Advanced Usage

#### Custom Provider Configuration

If you need to specify the api_key and/or the base_url for a provider, you can do so by passing the provider_config parameter to the `create_batch` function.

```python
batch = batchman.create_batch(
    name="my batch",
    provider="exxa",
    provider_config=ProviderConfig(
        api_key="your-api-key",
        url="https://api.example.com",
    )
)
```

### Security

Once a provider is configured (at batch creation time or later), the provider configuration **including the api_key** is
stored in the `providers_config.jsonl` file. This file should not be shared with others. The batches directories
only store hash references to this file, and are safe to share.

## Contributing

Contributions are welcome! Please see our [ (TODO) Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
