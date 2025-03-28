from pathlib import Path
from typing import Dict, Tuple, List, TYPE_CHECKING
from functools import partial
from prettytable import PrettyTable
from enum import Enum

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Button, Label, Markdown
from textual.screen import ModalScreen
from textual.containers import Grid
from textual import events

from ..providers.registry import ProviderRegistry
from ..batch_interfaces import UploadedBatch

if TYPE_CHECKING:
    from ..batchman import Batcher


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
            yield Grid(Label(self.message, id="question", markup=True), Label("Press Y to confirm", id="actionconfirm"), id="popup")
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
        ("q", "quit", "Quit"),
        ("c", "cancel", "Cancel"),
        ("d", "delete", "Delete"),
        ("p", "print", "Print paths"),
    ]

    def __init__(self, table: PrettyTable, batcher: "Batcher", changed_batches: Dict[str, Tuple[Enum, Enum]], errors: List[str]):
        self.table = table
        self.data_table = DataTable()
        self.batcher = batcher
        self.changed_batches = changed_batches
        self.errors = errors
        super().__init__()

    @staticmethod
    def _req_fmt(req_uid: str) -> str:
        return f"[chartreuse][bold]{req_uid}[/chartreuse][/bold]"

    def compose(self) -> ComposeResult:
        yield self.data_table
        yield Footer()

    def re_compute(self):
        self.data_table.clear()
        self.data_table.cursor_type = "row"
        self.data_table.zebra_stripes = True
        if not self.data_table.columns:
            self.data_table.add_columns(*self.table.field_names)
        for row in self.table.rows:
            self.data_table.add_row(*row, key=row[0])

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
                self.re_compute()
            except Exception as e:
                self.push_screen(PopupScreen(f"Failed to delete batch {self._req_fmt(batch_id)}: {e}"))

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
                    except Exception as e:
                        self.push_screen(PopupScreen(f"Failed to cancel batch {self._req_fmt(batch_id)}: {e}"))
            else:
                self.push_screen(PopupScreen(f"Batch {self._req_fmt(batch_id)} is not in an cancelable state"))

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
        self.push_screen(PopupScreen(f"Delete request {self._req_fmt(req_uid)}? It [bold]won't[/bold] cancel/remove it on the provider, "
                                     "but it will remove it [bold]permanently[/bold] locally", action_confirm=True),
                         callback=partial(self.deleting_batch, req_uid, coord))

    def action_print(self):
        provider_config_file_path = ProviderRegistry()._config_store.store_path
        self.push_screen(MarkdownPopup(f"### Current paths:\n\n"
                                   f"* **Current dir:** `{Path.cwd()}`\n"
                                   f"* **Batches dir:** `{self.batcher.batches_dir.resolve()}`\n"
                                   f"* **Provider config file:** `{provider_config_file_path}`"))

    def action_quit(self):
        self.app.exit()
        # self.push_screen(QuitScreen())