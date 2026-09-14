"""Modal generico para elegir un item de una lista (con busqueda opcional)."""
from __future__ import annotations

from typing import Generic, TypeVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

T = TypeVar("T")


class PickerScreen(ModalScreen[T | None], Generic[T]):
    """Modal con lista de opciones + busqueda + botones.

    Devuelve el item elegido (o None si el usuario cancela).
    Atajos:
      - Enter: acepta el item resaltado
      - Esc: cancela
      - Flechas arriba/abajo: navegar
      - Escribir en el input: filtra
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    def __init__(
        self,
        title: str,
        items: list[tuple[str, T]],   # (etiqueta a mostrar, valor)
        current: str | None = None,   # etiqueta del valor actual (para marcar)
        subtitle: str = "",
        searchable: bool = True,
    ) -> None:
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self._items = items
        self._current = current
        self._searchable = searchable
        self._filtered: list[tuple[str, T]] = list(items)
        self._selected_idx: int = 0

    # ---------------- compose ----------------
    def compose(self) -> ComposeResult:
        with Container(id="picker-dialog"):
            yield Static(f"[ {self._title} ]", id="picker-title")
            if self._subtitle:
                yield Static(self._subtitle, id="picker-subtitle")
            if self._searchable:
                yield Input(placeholder="Filtrar...", id="picker-search")
            with VerticalScroll(id="picker-scroll"):
                yield Vertical(id="picker-list")
            with Horizontal():
                yield Button("Aceptar (Enter)", variant="success", id="picker-ok")
                yield Button("Cancelar (Esc)", variant="error", id="picker-cancel")

    def on_mount(self) -> None:
        self._render_list()
        if self._searchable:
            self.query_one("#picker-search", Input).focus()
        else:
            self.query_one("#picker-list").focus()

    # ---------------- render ----------------
    def _render_list(self) -> None:
        from textual.widgets import Static as S

        container = self.query_one("#picker-list", Vertical)
        container.remove_children()

        if not self._filtered:
            container.mount(S("(sin resultados)", classes="picker-empty"))
            return

        # Limitar visualizacion para no saturar (200 max)
        for i, (label, _value) in enumerate(self._filtered[:200]):
            marker = ">" if i == self._selected_idx else " "
            is_current = label == self._current
            cur_mark = " ●" if is_current else ""
            cls = "picker-item picker-selected" if i == self._selected_idx else "picker-item"
            container.mount(S(f"{marker} {label}{cur_mark}", classes=cls))

        # Scroll al item seleccionado
        try:
            items = container.children
            if self._selected_idx < len(items):
                items[self._selected_idx].scroll_visible()
        except Exception:
            pass

    # ---------------- eventos ----------------
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "picker-search":
            return
        q = event.value.strip().lower()
        if not q:
            self._filtered = list(self._items)
        else:
            self._filtered = [
                (label, val)
                for (label, val) in self._items
                if q in label.lower()
            ]
        self._selected_idx = 0
        self._render_list()

    def on_key(self, event) -> None:
        if event.key == "up":
            self._move(-1)
            event.stop()
        elif event.key == "down":
            self._move(1)
            event.stop()
        elif event.key == "enter":
            self._accept()
            event.stop()

    def _move(self, delta: int) -> None:
        if not self._filtered:
            return
        self._selected_idx = (self._selected_idx + delta) % min(len(self._filtered), 200)
        self._render_list()

    def _accept(self) -> None:
        if not self._filtered:
            self.dismiss(None)
            return
        idx = min(self._selected_idx, len(self._filtered) - 1)
        _label, value = self._filtered[idx]
        self.dismiss(value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "picker-ok":
            self._accept()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
