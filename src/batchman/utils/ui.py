from pathlib import Path
from typing import Dict, Tuple, List
from functools import partial
from prettytable import PrettyTable
from enum import Enum
import click
from itertools import chain
import functools
from prettytable import PrettyTable
import asyncio

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Button, Label, Markdown
from textual.screen import ModalScreen
from textual.containers import Grid
from textual import events

from ..providers.registry import ProviderRegistry
from ..batch_interfaces import UploadedBatch
from ..batch_interfaces import UploadedBatch, EditableBatch, DownloadedBatch
from ..batchman import Batcher, LocalBatchStatus


class MarkdownPopup(ModalScreen):
    """A label that renders markdown."""
    def __init__(self, message: str):
        self.message = message
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Grid(Markdown(self.message, id="question"), id="markdown-popup")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.dismiss(result=(event.key == "y"))

class PopupScreen(ModalScreen):
    """Modal Screen with a popup message."""

    def __init__(self, message: str, action_confirm: bool = False):
        self.message = message
        self.action_confirm = action_confirm
        super().__init__()

    def compose(self) -> ComposeResult:
        if self.action_confirm:
            yield Grid(Label(self.message, id="question", markup=True), Label("Press y to confirm (anything else to cancel)", id="actionconfirm"), id="popup")
        else:
            yield Grid(Label(self.message, id="question"), id="popup")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.dismiss(result=(event.key == "y"))
        # self.app.pop_screen()

class QuitScreen(ModalScreen):
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("(Q)uit", variant="error", id="quit"),
            Button("(C)ancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        event.stop()
        if event.key == "q":
            self.app.exit()
        elif event.key == "c":
            self.app.pop_screen()

class TableApp(App):

    CSS = """
QuitScreen {
    align: center middle;
}
PopupScreen {
    align: center middle;
}
MarkdownPopup {
    align: center middle;
}

#popup {
    width: 70;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
    padding: 0 1;
    width: 70;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#actionconfirm {
    height: 1fr;
    width: 1fr;
    content-align: center bottom;
}

#question {
    column-span: 2;
    height: 1fr;
    width: 1fr;
    content-align: center middle;
}

Button {
    width: 100%;
}

#markdown-popup {
    width: 90vw;
    height: 90vh;
    border: thick $background 80%;
    background: $surface;
}"""

    BINDINGS = [
        ("q", "quit", "Quit ╰┈➤🚪"),
        ("c", "cancel", "Cancel 🚫"),
        ("D", "delete", "Delete ❌"),
        ("d", "download", "Download 📥"),
        ("p", "print", "Print paths 📄"),
        ("r", "reload", "Refresh table 🔄"),
    ]

    def __init__(self, dir: str):

        self.dir = dir
        super().__init__()
        self.data_table = DataTable()
        self.batcher = Batcher(batches_dir=Path(self.dir))
        # self.table, self.changed_batches, self.errors = self.set_table()


    def set_table(self) -> Tuple[PrettyTable, Dict[str, Tuple[LocalBatchStatus, LocalBatchStatus]], List[str]]:
        errors = self.batcher.sync_batches()
        editable_batches, uploaded_batches, downloaded_batches, listing_errors = self.batcher.list_batches()

        errors.extend(listing_errors)

        changed_batches = []

        waiting_batches = [batch for batch in uploaded_batches if batch.status in [LocalBatchStatus.VALIDATING, LocalBatchStatus.REGISTERED, LocalBatchStatus.IN_PROGRESS]]

        if waiting_batches:
            click.echo(
                f"Found {len(editable_batches)+len(uploaded_batches)+len(downloaded_batches)} valid batches and {len(waiting_batches)} batches to synchronize: Syncing...  ",
                nl=False,
            )
            statuses = {batch.unique_id: batch.status for batch in set(uploaded_batches + editable_batches + downloaded_batches)}
            self.batcher.sync_batches()
            editable_batches, uploaded_batches, downloaded_batches, listing_errors = self.batcher.list_batches()
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

        return table, changed_batches, errors


    @staticmethod
    def _req_fmt(req_uid: str) -> str:
        return f"[chartreuse][bold]{req_uid}[/chartreuse][/bold]"

    def compose(self) -> ComposeResult:
        yield self.data_table
        yield Footer()

    def re_compute(self):
        self.table, self.changed_batches, self.errors = self.set_table()
        self.data_table.clear()
        self.data_table.cursor_type = "row"
        self.data_table.zebra_stripes = True
        if not self.data_table.columns:
            self.data_table.add_columns(*self.table.field_names)
        for row in self.table.rows:
            self.data_table.add_row(*row, key=row[0])
        self.query_one(DataTable).loading = False
        # self.data_table.loading = False

    def on_mount(self) -> None:
        self.re_compute()
        if self.errors:
            self.push_screen(PopupScreen("Errors: " + "\n".join(self.errors)))
        if self.changed_batches:
            self.push_screen(PopupScreen("Changed batches: " + "\n".join(
                [f"{self._req_fmt(batch_id)}: {status_old.value} -> {status_new.value}" for batch_id, (status_old, status_new) in self.changed_batches.items()])))

    def deleting_batch(self, batch_id: str, row_index: int, confirm: bool):
        if confirm:
            try:
                self.batcher.delete_batch(unique_id=batch_id)
                self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} deleted"))
                self.table.del_row(row_index=row_index)
                self.action_reload()
            except Exception as e:
                self.push_screen(PopupScreen(f"Failed to delete batch {self._req_fmt(batch_id)}:\n{e}"))

    def cancelling_batch(self, batch_id: str, confirm: bool):
        if confirm:
            batch = self.batcher.load_batch(unique_id=batch_id)
            if isinstance(batch, UploadedBatch):
                if batch.status.value == "cancelled":
                    self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} is already cancelled"))
                else:
                    try:
                        batch.cancel()
                        self.push_screen(PopupScreen(f"Canceling of batch {self._req_fmt(batch_id)} confirmed"))
                        self.action_reload()
                    except Exception as e:
                        self.push_screen(PopupScreen(f"Failed to cancel batch {self._req_fmt(batch_id)}:\n{e}"))
            else:
                self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} is not in a cancelable state"))

    def action_cancel(self):
        table = self.data_table
        table.cursor_type = "row"
        coord = table.cursor_coordinate.row
        req_uid = table.get_row_at(coord)[0]
        self.push_screen(PopupScreen(f"Cancel request {self._req_fmt(req_uid)}?", action_confirm=True),
                         callback=partial(self.cancelling_batch, req_uid))

    def action_delete(self):
        table = self.data_table
        table.cursor_type = "row"
        coord = table.cursor_coordinate.row
        req_uid = table.get_row_at(coord)[0]
        self.push_screen(PopupScreen(f"[bold red]Delete[/bold red] request {self._req_fmt(req_uid)}? It [bold]won't[/bold] cancel/remove it on the provider, "
                                     "but it will remove it [bold]permanently[/bold] locally", action_confirm=True),
                         callback=partial(self.deleting_batch, req_uid, coord))

    def action_print(self):
        provider_config_file_path = ProviderRegistry()._config_store.store_path
        self.push_screen(MarkdownPopup(f"### Current paths:\n\n"
                                   f"* **Current dir:** `{Path.cwd()}`\n"
                                   f"* **Batches dir:** `{self.batcher.batches_dir.resolve()}`\n"
                                   f"* **Provider config file:** `{provider_config_file_path}`"))

    def action_reload(self):
        self.data_table.loading = True
        self.call_after_refresh(self.re_compute)

    def downloading_batch(self, batch_id: str, confirm: bool):
        if confirm:
            batch = self.batcher.load_batch(unique_id=batch_id)
            if isinstance(batch, DownloadedBatch):
                self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} is already downloaded"))
            elif isinstance(batch, EditableBatch):
                self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} has not been uploaded yet"))
            else:
                try:
                    batch.download()
                    self.push_screen(PopupScreen(f"Downloading batch {self._req_fmt(batch_id)}"))
                    self.action_reload()
                except Exception as e:
                    self.push_screen(PopupScreen(f"Failed to download batch {self._req_fmt(batch_id)}:\n{e}"))

    def action_download(self):
        table = self.data_table
        table.cursor_type = "row"
        coord = table.cursor_coordinate.row
        req_uid = table.get_row_at(coord)[0]
        self.push_screen(PopupScreen(f"Download request {self._req_fmt(req_uid)}?", action_confirm=True),
                         callback=partial(self.downloading_batch, req_uid))

    def action_quit(self):
        self.app.exit()
        # self.push_screen(QuitScreen())