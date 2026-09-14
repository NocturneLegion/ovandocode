"""Modal de confirmacion de permisos."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class PermissionScreen(ModalScreen[bool]):
    """Pregunta al usuario si autoriza un comando.

    Devuelve True si autoriza, False si rechaza.
    Atajos: 'y' = yes, 'n' = no, Escape = no.
    """

    BINDINGS = [
        Binding("y", "yes", "Si", show=True),
        Binding("n", "no", "No", show=True),
        Binding("escape", "no", "No", show=False),
    ]

    def __init__(self, command: str, reason: str) -> None:
        super().__init__()
        self.command = command
        self.reason = reason

    def compose(self) -> ComposeResult:
        with Container(id="perm-dialog"):
            yield Static("[ PERMISO REQUERIDO ]", id="perm-title")
            yield Static(f"Comando: {self.command}", id="perm-cmd")
            yield Static(f"Razon:   {self.reason}", id="perm-reason")
            with Horizontal():
                yield Button("Si (y)", variant="success", id="btn-yes")
                yield Button("No (n)", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)
