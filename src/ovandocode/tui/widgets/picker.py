"""Modal generico para elegir un item de una lista (con scroll y busqueda)."""
from __future__ import annotations

from typing import Generic, TypeVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

T = TypeVar("T")


class PickerScreen(ModalScreen[T | None], Generic[T]):
    """Modal con lista scrolleable + busqueda + navegacion por teclado.

    Devuelve el item elegido (o None si cancela).

    Atajos:
      - Flechas arriba/abajo: navegar
      - Enter: aceptar
      - Esc: cancelar
      - Escribir en el input: filtra
      - PageUp / PageDown: saltar de a 10
      - Home / End: ir al primero / ultimo
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
        Binding("up", "move_up", "Arriba", show=False, priority=True),
        Binding("down", "move_down", "Abajo", show=False, priority=True),
        Binding("pageup", "page_up", "Pag arriba", show=False, priority=True),
        Binding("pagedown", "page_down", "Pag abajo", show=False, priority=True),
        Binding("home", "go_home", "Inicio", show=False, priority=True),
        Binding("end", "go_end", "Fin", show=False, priority=True),
        Binding("enter", "accept", "Aceptar", show=False, priority=True),
    ]

    def __init__(
        self,
        title: str,
        items: list[tuple[str, T]],
        current: str | None = None,
        subtitle: str = "",
        searchable: bool = True,
    ) -> None:
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self._items = list(items)
        self._current = current
        self._searchable = searchable
        self._filtered: list[tuple[str, T]] = list(items)
        self._selected_idx: int = 0

        # Posicionar en el item actual si existe
        if current is not None:
            for i, (label, _) in enumerate(items):
                if label == current:
                    self._selected_idx = i
                    break

    # ---------------- compose ----------------
    def compose(self) -> ComposeResult:
        with Container(id="picker-dialog"):
            yield Static(f"[ {self._title} ]", id="picker-title")
            if self._subtitle:
                yield Static(self._subtitle, id="picker-subtitle")
            if self._searchable:
                yield Input(placeholder="Filtrar...", id="picker-search")
            # VerticalScroll es quien maneja el scroll de la lista
            with VerticalScroll(id="picker-scroll"):
                yield Static("", id="picker-list")
            yield Static("", id="picker-counter")
            with Horizontal(id="picker-buttons"):
                yield Button("Aceptar (Enter)", variant="success", id="picker-ok")
                yield Button("Cancelar (Esc)", variant="error", id="picker-cancel")

    def on_mount(self) -> None:
        self._render_list()
        if self._searchable:
            self.query_one("#picker-search", Input).focus()
        else:
            self.query_one("#picker-scroll").focus()

    # ---------------- render ----------------
    def _render_list(self) -> None:
        """Renderiza la lista completa como un solo Static multilinea."""
        list_widget = self.query_one("#picker-list", Static)

        if not self._filtered:
            list_widget.update("(sin resultados)")
            self._update_counter()
            return

        lines: list[str] = []
        for i, (label, _value) in enumerate(self._filtered):
            marker = ">" if i == self._selected_idx else " "
            is_current = label == self._current
            cur_mark = " ●" if is_current else ""
            lines.append(f"{marker} {label}{cur_mark}")

        list_widget.update("\n".join(lines))
        self._update_counter()
        self._scroll_to_selected()

    def _update_counter(self) -> None:
        counter = self.query_one("#picker-counter", Static)
        total = len(self._items)
        shown = len(self._filtered)
        idx = self._selected_idx + 1 if self._filtered else 0
        if shown == total:
            counter.update(f"[dim]{idx} / {shown}[/]")
        else:
            counter.update(f"[dim]{idx} / {shown} (filtrado de {total})[/]")

    def _scroll_to_selected(self) -> None:
        """Asegura que el item seleccionado este visible."""
        if not self._filtered:
            return
        try:
            scroll = self.query_one("#picker-scroll", VerticalScroll)
            # Cada item ocupa 1 linea. El viewport tiene una altura visible.
            # Desplazamos para centrar el item seleccionado.
            viewport_h = scroll.size.height or 10
            target_y = max(0, self._selected_idx - viewport_h // 2)
            scroll.scroll_y = target_y
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "picker-ok":
            self.action_accept()
        else:
            self.dismiss(None)

    # ---------------- acciones de teclado ----------------
    def _move(self, delta: int) -> None:
        if not self._filtered:
            return
        n = len(self._filtered)
        self._selected_idx = (self._selected_idx + delta) % n
        self._render_list()

    def action_move_up(self) -> None:
        self._move(-1)

    def action_move_down(self) -> None:
        self._move(1)

    def action_page_up(self) -> None:
        self._move(-10)

    def action_page_down(self) -> None:
        self._move(10)

    def action_go_home(self) -> None:
        if self._filtered:
            self._selected_idx = 0
            self._render_list()

    def action_go_end(self) -> None:
        if self._filtered:
            self._selected_idx = len(self._filtered) - 1
            self._render_list()

    def action_accept(self) -> None:
        if not self._filtered:
            self.dismiss(None)
            return
        idx = min(self._selected_idx, len(self._filtered) - 1)
        _label, value = self._filtered[idx]
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
