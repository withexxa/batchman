import click
from pathlib import Path
from typing import Optional
from itertools import chain
import functools

from prettytable import PrettyTable

from batchman.models.enums import LocalBatchStatus
from batchman.batch_interfaces import UploadedBatch, EditableBatch, DownloadedBatch
from .batchman import Batcher



def common_params(func):
    @click.option("--dir", type=click.Path(exists=False), default="batches", 
                 help="The directory to list the batches from. You shouldn't need to change this.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@click.group()
@click.option("--dir", type=click.Path(exists=False), default=None, 
                 help="The directory to list the batches from. You shouldn't need to change this.")
def cli(dir: Optional[str]) -> None:
    context = click.get_current_context()
    context.obj = {"batches_dir": dir}
    """Manage batches of requests."""


@cli.command()
@common_params
@click.pass_context
def list(ctx: click.Context, dir: str) -> None:
    """List all batches."""
    dir = ctx.obj["batches_dir"] or dir
    batcher = Batcher(batches_dir=Path(dir))

    errors = []

    editable_batches, uploaded_batches, downloaded_batches, listing_errors = batcher.list_batches()

    errors.extend(listing_errors)

    uncompleted_batches = [
        batch for batch in chain(editable_batches, uploaded_batches)
    ]

    if uncompleted_batches:
        click.echo(
            f"Found {len(uncompleted_batches)+ len(downloaded_batches)} valid batches and {len(uncompleted_batches)} batches to synchronize: Syncing...  ",
            nl=False,
        )

        batcher.sync_batches()

        click.echo("Done")

    else:
        click.echo(f"Found {len(downloaded_batches)} batches.")

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

    click.echo(table)

    if errors:
        click.echo("Errors:")
        for error in errors:
            click.echo(f"  • {error}")


@cli.command()
@common_params
@click.pass_context
def sync(ctx: click.Context, dir: str) -> None:
    """Synchronize all batches."""
    dir = ctx.obj["batches_dir"] or dir
    batcher = Batcher(batches_dir=Path(dir))
    batcher.sync_batches()
    click.echo("Synchronization completed")

@cli.command()
@click.argument("batch_id",type=str, required=True)
@common_params
@click.pass_context
def cancel(ctx: click.Context, dir: str, batch_id: str) -> None:
    """Cancel a batch given its unique ID."""
    dir = ctx.obj["batches_dir"] or dir
    batcher = Batcher(batches_dir=Path(dir))
    batch = batcher.load_batch(unique_id=batch_id)
    if isinstance(batch, UploadedBatch):
        batch.cancel()
        click.echo(f"Batch {batch.params.name} canceled")
    elif isinstance(batch, EditableBatch):
        click.echo("Batch is editable, can't cancel it before upload!")
    elif isinstance(batch, DownloadedBatch):
        click.echo("Batch is downloaded, can't cancel anymore")
    else:
        click.echo("Batch is not in an uploadable state")


if __name__ == "__main__":
    cli()