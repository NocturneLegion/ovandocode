"""Modal para elegir/cambiar/ver estado de proveedores LLM."""
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


# Resultado del modal: (accion, provider_id) o None
#   ("switch", "groq")     -> cambiar a ese proveedor
#   ("configure", "groq")  -> abrir el editor de la key para ese proveedor
#   ("configure", None)    -> abrir el editor vacio
class ProviderPickerScreen(ModalScreen["tuple[str, str | None] | None"]):
    """Lista de proveedores con su estado de credenciales."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
        Binding("c", "configure_blank", "Configurar", show=True),
    ]

    def __init__(self, active: str | None = None) -> None:
        super().__init__()
        self.active = active

    # ---------------- compose ----------------
    def compose(self) -> ComposeResult:
        with Container(id="prov-picker"):
            yield Static("[ Proveedores ]", id="prov-title")
            yield Static(
                "Enter / click en uno para usarlo (o configurarlo si falta la key)",
                id="prov-hint",
            )

            with VerticalScroll(id="prov-scroll"):
                yield Vertical(id="prov-list")

            with Horizontal(id="prov-buttons"):
                yield Button("Configurar...", variant="primary", id="btn-prov-config")
                yield Button("Cerrar", variant="error", id="btn-prov-close")

    def on_mount(self) -> None:
        self._render_list()

    def _render_list(self) -> None:
        """Renderiza la lista con estado actual de cada proveedor."""
        container = self.query_one("#prov-list", Vertical)
        container.remove_children()

        cm = get_credentials()
        local = local_providers()

        for label, pid in PROVIDER_CHOICES:
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

            marker = "*" if pid == self.active else " "
            text = f"{marker}  {label:<26} {status}"

            if pid == self.active:
                cls += " prov-active"

            container.mount(Static(text, name=pid, classes=cls))

    # ---------------- eventos ----------------
    def on_click(self, event: Click) -> None:
        widget = getattr(event, "widget", None)
        if widget is None:
            return
        pid = getattr(widget, "name", None)
        if not pid:
            return
        self._handle_provider_choice(pid)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-prov-config":
            self.dismiss(("configure", None))
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

    # ---------------- acciones ----------------
    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_configure_blank(self) -> None:
        self.dismiss(("configure", None))
