import click
from pathlib import Path
from typing import Optional
from itertools import chain
import functools
from prettytable import PrettyTable

from .batch_interfaces import UploadedBatch, EditableBatch, DownloadedBatch
from .batchman import Batcher, LocalBatchStatus
from .utils.ui import TableApp
from .utils.logging import logger


@click.command()
@click.option("--dir", type=click.Path(exists=False), default=Path.home() / ".batchman" / "batches",
                 help="The directory to list the batches from. You shouldn't need to change this.")
def cli(dir: Optional[str]) -> None:
    """Manage batches of requests."""

    batcher = Batcher(batches_dir=Path(dir))

    errors = []

    editable_batches, uploaded_batches, downloaded_batches, listing_errors = batcher.list_batches()

    errors.extend(listing_errors)

    changed_batches = []

    waiting_batches = [batch for batch in uploaded_batches if batch.status in [LocalBatchStatus.VALIDATING, LocalBatchStatus.REGISTERED, LocalBatchStatus.IN_PROGRESS]]

    if waiting_batches:
        click.echo(
            f"Found {len(editable_batches)+len(uploaded_batches)+len(downloaded_batches)} valid batches and {len(waiting_batches)} batches to synchronize: Syncing...  ",
            nl=False,
        )
        statuses = {batch.unique_id: batch.status for batch in set(uploaded_batches + editable_batches + downloaded_batches)}
        batcher.sync_batches()
        editable_batches, uploaded_batches, downloaded_batches, listing_errors = batcher.list_batches()
        errors = listing_errors
        new_statuses = {batch.unique_id: batch.status for batch in set(uploaded_batches + editable_batches + downloaded_batches)}
        changed_batches = {batch_id: (statuses[batch_id], new_statuses[batch_id]) for batch_id in statuses if statuses[batch_id] != new_statuses[batch_id]}
        click.echo("Done")

    else:
        click.echo(f"Found {len(editable_batches)+len(uploaded_batches)+len(downloaded_batches)} batches.")

    table = PrettyTable(["Local ID", "Name", "Status", "Provider", "Remote ID"])

    fields_getters = [
        ("unique_id", lambda batch: batch.params.unique_id),
        ("name", lambda batch: batch.params.name),
        ("status", lambda batch: batch.status.value),
        ("provider", lambda batch: batch.params.provider.get("name", "N/A")),
        ("remote_id", lambda batch: batch.remote_id or "N/A"),
    ]

    for batch in chain(editable_batches, uploaded_batches, downloaded_batches):
        row = []
        for field, getter in fields_getters:
            try:
                row.append(getter(batch))
            except Exception as e:
                row.append("ERROR")
                errors.append(
                    f"Batch {batch.params.name}:{batch.params.unique_id} - {field}: {e}"
                )
        table.add_row(row)

    app = TableApp(table, batcher, changed_batches, errors)
    app.run()


if __name__ == "__main__":
    cli()