"""Modal para elegir/cambiar/ver estado de proveedores LLM.

Navegacion:
  - Flechas arriba/abajo: mover seleccion
  - Enter: usar/configurar el proveedor seleccionado
  - Click simple: seleccionar (sin ejecutar)
  - Doble click: usar/configurar directamente
  - 'c': configurar (abre editor en blanco)
  - Esc: cancelar
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ovandocode.config import get_credentials
from ovandocode.providers import REGISTRY

# Lista canonica: (etiqueta a mostrar, id en REGISTRY)
PROVIDER_CHOICES: list[tuple[str, str]] = [
    ("OpenRouter", "openrouter"),
    ("OpenAI", "openai"),
    ("Anthropic (Claude)", "anthropic"),
    ("Google Gemini", "gemini"),
    ("Groq", "groq"),
    ("DeepSeek", "deepseek"),
    ("Mistral", "mistral"),
    ("xAI (Grok)", "xai"),
    ("Ollama (local)", "ollama"),
    ("LM Studio (local)", "lmstudio"),
]


def local_providers() -> set[str]:
    """Proveedores que no requieren API key."""
    return {name for name, cls in REGISTRY.items() if not cls.requires_api_key}


class ProviderPickerScreen(ModalScreen["tuple[str, str | None] | None"]):
    """Lista de proveedores con su estado de credenciales."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
        Binding("c", "configure_blank", "Configurar", show=True),
        Binding("up", "move_up", "Arriba", show=False, priority=True),
        Binding("down", "move_down", "Abajo", show=False, priority=True),
        Binding("enter", "accept", "Elegir", show=True, priority=True),
    ]

    def __init__(self, active: str | None = None) -> None:
        super().__init__()
        self.active = active
        self._selected_idx: int = 0
        self._last_click_idx: int | None = None

        # Posicionar en el proveedor activo si existe
        if active is not None:
            for i, (_label, pid) in enumerate(PROVIDER_CHOICES):
                if pid == active:
                    self._selected_idx = i
                    break

    # ---------------- compose ----------------
    def compose(self) -> ComposeResult:
        with Container(id="prov-picker"):
            yield Static("[ Proveedores ]", id="prov-title")
            yield Static(
                "Flechas para moverte  |  Enter para elegir  |  Click para seleccionar  |  Doble click para usar",
                id="prov-hint",
            )

            with VerticalScroll(id="prov-scroll"):
                yield Vertical(id="prov-list")

            with Horizontal(id="prov-buttons"):
                yield Button("Configurar...", variant="primary", id="btn-prov-config")
                yield Button("Cerrar", variant="error", id="btn-prov-close")

    def on_mount(self) -> None:
        self._render_list()
        self._scroll_to_selected()

    # ---------------- render ----------------
    def _render_list(self) -> None:
        """Renderiza la lista con estado actual de cada proveedor."""
        container = self.query_one("#prov-list", Vertical)
        container.remove_children()

        cm = get_credentials()
        local = local_providers()

        for i, (label, pid) in enumerate(PROVIDER_CHOICES):
            if pid in local:
                status = "(local, sin key)"
                cls = "prov-item prov-local"
            else:
                source = cm.source_of(pid)
                if source != "none":
                    status = f"OK  ({source})"
                    cls = "prov-item prov-ok"
                else:
                    status = "--  sin configurar"
                    cls = "prov-item prov-missing"

            active_marker = "*" if pid == self.active else " "
            pointer = ">" if i == self._selected_idx else " "
            text = f"{pointer} {active_marker} {label:<26} {status}"

            if pid == self.active:
                cls += " prov-active"
            if i == self._selected_idx:
                cls += " prov-selected"

            container.mount(Static(text, name=pid, classes=cls))

    def _scroll_to_selected(self) -> None:
        """Asegura que el item seleccionado este visible."""
        try:
            scroll = self.query_one("#prov-scroll", VerticalScroll)
            viewport_h = scroll.size.height or 10
            target_y = max(0, self._selected_idx - viewport_h // 2)
            scroll.scroll_y = target_y
        except Exception:
            pass

    # ---------------- eventos ----------------
    def on_click(self, event: Click) -> None:
        widget = getattr(event, "widget", None)
        if widget is None:
            return
        pid = getattr(widget, "name", None)
        if not pid:
            return

        # Buscar indice del proveedor clickeado
        target_idx: int | None = None
        for i, (_label, p) in enumerate(PROVIDER_CHOICES):
            if p == pid:
                target_idx = i
                break
        if target_idx is None:
            return

        # Doble click en el mismo item = ejecutar directo
        if self._last_click_idx == target_idx:
            self._last_click_idx = None
            self._handle_provider_choice(pid)
            return

        # Primer click = solo seleccionar
        self._last_click_idx = target_idx
        self._selected_idx = target_idx
        self._render_list()
        self._scroll_to_selected()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-prov-config":
            # Configurar el proveedor actualmente seleccionado
            idx = max(0, min(self._selected_idx, len(PROVIDER_CHOICES) - 1))
            _label, pid = PROVIDER_CHOICES[idx]
            self.dismiss(("configure", pid))
        elif event.button.id == "btn-prov-close":
            self.dismiss(None)

    def _handle_provider_choice(self, pid: str) -> None:
        # Local (Ollama, LM Studio) -> solo cambiar
        if pid in local_providers():
            self.dismiss(("switch", pid))
            return

        # Tiene key configurada -> cambiar
        source = get_credentials().source_of(pid)
        if source != "none":
            self.dismiss(("switch", pid))
            return

        # No tiene key -> abrir editor
        self.dismiss(("configure", pid))

    # ---------------- acciones de teclado ----------------
    def _move(self, delta: int) -> None:
        n = len(PROVIDER_CHOICES)
        if n == 0:
            return
        self._selected_idx = (self._selected_idx + delta) % n
        self._render_list()
        self._scroll_to_selected()

    def action_move_up(self) -> None:
        self._move(-1)

    def action_move_down(self) -> None:
        self._move(1)

    def action_accept(self) -> None:
        if not PROVIDER_CHOICES:
            return
        idx = max(0, min(self._selected_idx, len(PROVIDER_CHOICES) - 1))
        _label, pid = PROVIDER_CHOICES[idx]
        self._handle_provider_choice(pid)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_configure_blank(self) -> None:
        self.dismiss(("configure", None))