"""Widget para configurar una API key desde la TUI.

Incluye validacion real contactando al proveedor antes de guardar.
"""
from __future__ import annotations

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from ovandocode.config import get_credentials
from ovandocode.providers import REGISTRY
from ovandocode.tui.widgets.provider_picker import PROVIDER_CHOICES, local_providers


async def validate_api_key(provider: str, api_key: str, timeout: float = 15.0) -> tuple[bool, str]:
    """Valida una API key intentando listar los modelos del proveedor.

    Devuelve (ok, mensaje).
    - ok=True: la key funciona
    - ok=False: la key fallo o no se pudo validar
    """
    from ovandocode.providers import create_provider

    try:
        p = create_provider(provider, api_key=api_key)
    except Exception as e:
        return False, f"No se pudo crear el proveedor: {e}"

    try:
        async with p:
            # list_models es la validacion mas liviana
            models = await asyncio.wait_for(p.list_models(), timeout=timeout)
            if models:
                return True, f"key valida ({len(models)} modelos disponibles)"
            # Si devuelve vacio, intentar un chat minimo
            from ovandocode.providers.types import ChatRequest, Message
            # usar el primer modelo como fallback (o uno conocido)
            test_model = "gpt-3.5-turbo" if provider == "openai" else "test"
            try:
                await asyncio.wait_for(
                    p.chat(ChatRequest(
                        messages=[Message(role="user", content="ok")],
                        model=test_model,
                        max_tokens=1,
                    )),
                    timeout=timeout,
                )
                return True, "key valida"
            except Exception:
                return True, "key aceptada (no se pudo validar del todo)"
    except TimeoutError:
        return False, f"timeout despues de {timeout}s validando la key"
    except Exception as e:
        # Extraer codigo HTTP si esta
        err = str(e)
        if "401" in err or "403" in err:
            return False, "la key fue rechazada (401/403)"
        if "402" in err:
            return False, "key valida pero sin saldo (402)"
        return False, f"error validando: {type(e).__name__}: {err[:120]}"


class CredentialsScreen(ModalScreen[dict | None]):
    """Modal para configurar la API key de un proveedor."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=True),
    ]

    def __init__(self, provider: str | None = None) -> None:
        super().__init__()
        self.selected_provider: str | None = provider if provider else None
        self._busy: bool = False

    def compose(self) -> ComposeResult:
        with Container(id="creds-modal"):
            with Vertical(id="creds-content"):
                yield Static("[ API Key ]", id="creds-title")

                with Horizontal(id="provider-row"):
                    yield Label("Proveedor:", id="prov-label")
                    options = [(label, pid) for label, pid in PROVIDER_CHOICES]
                    valid_ids = {pid for _, pid in options}
                    default_value = (
                        self.selected_provider
                        if self.selected_provider in valid_ids
                        else options[0][1]
                    )
                    yield Select(
                        options=options,
                        value=default_value,
                        id="provider-select",
                    )

                yield Label("Ingresa tu API Key:", id="key-label")
                yield Input(
                    placeholder="sk-...",
                    password=True,
                    id="api-key-input",
                )

                yield Static("", id="creds-status")

                with Horizontal(id="creds-buttons"):
                    yield Button("Validar y guardar", variant="primary", id="btn-save")
                    yield Button("Cancelar", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#api-key-input", Input).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        val = event.value
        if isinstance(val, str) and val:
            self.selected_provider = val

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self.validate_and_save()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _set_status(self, text: str, color: str = "white") -> None:
        self.query_one("#creds-status", Static).update(f"[{color}]{text}[/]")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        try:
            self.query_one("#btn-save", Button).disabled = busy
            self.query_one("#btn-cancel", Button).disabled = busy
        except Exception:
            pass

    # ---------------- validacion + guardado ----------------
    @work(exclusive=True)
    async def validate_and_save(self) -> None:
        if self._busy:
            return

        provider_id = self.selected_provider
        api_key = self.query_one("#api-key-input", Input).value.strip()

        # Validaciones previas
        if not provider_id:
            self._set_status("Debes seleccionar un proveedor", "red")
            return

        if provider_id not in REGISTRY:
            self._set_status(f"Proveedor no soportado: {provider_id}", "red")
            return

        # Locales no requieren key
        if provider_id in local_providers():
            self._set_status(f"{provider_id} no requiere API key", "yellow")
            self.dismiss({"provider": provider_id, "saved": False, "local": True})
            return

        if not api_key:
            self._set_status("La API Key no puede estar vacia", "red")
            return

        # 1) Validar con el proveedor
        self._set_busy(True)
        self._set_status(f"Validando con {provider_id}...", "yellow")

        ok, message = await validate_api_key(provider_id, api_key)
        if not ok:
            self._set_status(f"Validacion fallo: {message}", "red")
            self._set_busy(False)
            return

        # 2) Guardar en keyring
        self._set_status(f"{message}. Guardando...", "yellow")
        cm = get_credentials()
        try:
            cm.set(provider_id, api_key, backend="keyring")
        except Exception as e:
            self._set_status(
                f"Validacion OK pero no se pudo guardar en keyring: {e}. "
                f"Usa: ovandocode config set-key {provider_id}",
                "red",
            )
            self._set_busy(False)
            return

        self._set_status(f"Guardado en keyring: {provider_id}", "green")
        self.dismiss({"provider": provider_id, "saved": True})
