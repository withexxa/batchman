import click
from pathlib import Path
from typing import Optional

from .utils.ui import TableApp
from .utils.logging import logger


@click.command()
@click.option("--dir", type=click.Path(exists=False), default=Path.home() / ".batchman" / "batches",
                 help="The directory to list the batches from. You shouldn't need to change this.")
def cli(dir: Optional[str]) -> None:
    """Manage batches of requests."""

    app = TableApp(dir)
    app.run()


if __name__ == "__main__":
    cli()