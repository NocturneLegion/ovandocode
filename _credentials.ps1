# _credentials.ps1 - Script de migración de funcionalidad Credentials a OvandoCode
# Ejecutar desde: D:\Trabajo\OvandoCode

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Iniciando Migración de Credenciales " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$ProjectRoot = "D:\Trabajo\OvandoCode"
$WidgetsDir = Join-Path $ProjectRoot "src\ovandocode\tui\widgets"
$CredentialsFile = Join-Path $WidgetsDir "credentials.py"
$InitFile = Join-Path $WidgetsDir "__init__.py"
$AppFile = Join-Path $ProjectRoot "src\ovandocode\tui\app.py"
$ThemeFile = Join-Path $ProjectRoot "src\ovandocode\tui\theme.tcss"

$Errors = 0

# 1. Crear directorio si no existe
if (!(Test-Path $WidgetsDir)) {
    New-Item -ItemType Directory -Force -Path $WidgetsDir | Out-Null
    Write-Host "[OK] Directorio widgets creado." -ForegroundColor Green
} else {
    Write-Host "[OK] Directorio widgets ya existe." -ForegroundColor Gray
}

# 2. Crear archivo credentials.py
Write-Host "Creando credentials.py..." -NoNewline
try {
    $PythonCode = @'
"""
Widget para gestión de credenciales (API Keys) en OvandoCode.
Permite configurar claves API directamente desde la TUI sin editar .env manualmente.
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static, Input, Button, Label, Select
from textual.binding import Binding
from textual.message import Message
import os
from pathlib import Path

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

class CredentialsScreen(ModalScreen[dict | None]):
    """Pantalla modal para configurar una API Key específica."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancelar"),
        Binding("enter", "submit", "Guardar"),
    ]

    class Saved(Message):
        def __init__(self, provider: str, source: str):
            self.provider = provider
            self.source = source
            super().__init__()

    def __init__(self, provider: str | None = None):
        super().__init__()
        self.selected_provider = provider
        self.providers = [
            ("OpenAI", "openai"),
            ("Anthropic", "anthropic"),
            ("Google Gemini", "google"),
            ("Groq", "groq"),
            ("Ollama", "ollama"),
            ("Azure OpenAI", "azure"),
            ("Hugging Face", "huggingface"),
        ]

    def compose(self) -> ComposeResult:
        with Container(id="creds-modal"):
            with Vertical(id="creds-content"):
                yield Static("🔑 Configuración de API Key", id="creds-title")
                
                with Horizontal(id="provider-row"):
                    yield Label("Proveedor:", id="prov-label")
                    options = [(name, id) for name, id in self.providers]
                    initial_value = self.selected_provider if self.selected_provider else ""
                    yield Select(
                        options=options,
                        value=initial_value,
                        id="provider-select",
                        allow_blank=False
                    )

                yield Label("Ingresa tu API Key:", id="key-label")
                yield Input(
                    placeholder="sk-...",
                    password=True,
                    id="api-key-input"
                )
                
                with Horizontal(id="creds-buttons"):
                    yield Button("Guardar", variant="primary", id="btn-save")
                    yield Button("Cancelar", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#api-key-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self.save_credentials()

    def on_select_changed(self, event: Select.Changed) -> None:
        self.selected_provider = event.value

    def save_credentials(self) -> None:
        provider_id = self.selected_provider
        api_key = self.query_one("#api-key-input", Input).value.strip()

        if not api_key:
            self.notify("⚠️ La API Key no puede estar vacía", severity="warning")
            return

        if not provider_id:
            self.notify("⚠️ Debes seleccionar un proveedor", severity="warning")
            return

        success = False
        source = "desconocido"

        # Intentar guardar en Keyring primero (más seguro)
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password("ovandocode", provider_id, api_key)
                success = True
                source = "keyring (Seguro)"
            except Exception:
                pass 

        # Si no hubo keyring o falló, guardar en .env
        if not success:
            try:
                env_path = Path.home() / ".ovandocode" / ".env"
                env_path.parent.mkdir(parents=True, exist_ok=True)
                
                lines = []
                var_name = f"{provider_id.upper()}_API_KEY"
                found = False
                
                if env_path.exists():
                    with open(env_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        if line.startswith(f"{var_name}="):
                            new_lines.append(f"{var_name}={api_key}\n")
                            found = True
                        else:
                            new_lines.append(line)
                    lines = new_lines

                if not found:
                    lines.append(f"\n{var_name}={api_key}\n")

                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                
                success = True
                source = ".env local"
            except Exception as e:
                self.notify(f"❌ Error al guardar: {str(e)}", severity="error")
                return

        if success:
            self.notify(f"✅ API Key guardada en {source}", severity="information")
            self.dismiss({"provider": provider_id, "source": source})
        else:
            self.notify("❌ No se pudo guardar la credencial", severity="error")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        self.save_credentials()


class CredentialsListScreen(ModalScreen[bool]):
    """Pantalla para listar el estado de todas las credenciales."""
    
    BINDINGS = [
        Binding("escape", "close", "Cerrar"),
        Binding("c", "configure", "Configurar"),
    ]

    def __init__(self):
        super().__init__()
        self.providers_info = [
            ("OpenAI", "openai", "OPENAI_API_KEY"),
            ("Anthropic", "anthropic", "ANTHROPIC_API_KEY"),
            ("Google Gemini", "google", "GOOGLE_API_KEY"),
            ("Groq", "groq", "GROQ_API_KEY"),
            ("Ollama", "ollama", None),
            ("Azure OpenAI", "azure", "AZURE_OPENAI_API_KEY"),
            ("Hugging Face", "huggingface", "HUGGINGFACE_API_KEY"),
        ]

    def compose(self) -> ComposeResult:
        with Container(id="creds-list-modal"):
            with Vertical(id="creds-list-content"):
                yield Static("📋 Estado de Proveedores", id="list-title")
                
                with Vertical(id="providers-list"):
                    for name, pid, env_var in self.providers_info:
                        status, source = self.check_status(pid, env_var)
                        status_icon = "✅" if status else "❌"
                        source_text = f"({source})" if source else ""
                        label_text = f"{status_icon} {name} {source_text}"
                        
                        item_class = "provider-item-configured" if status else "provider-item-missing"
                        yield Static(label_text, classes=item_class, name=pid)

                yield Static("Presiona 'C' para configurar un proveedor faltante.", id="list-hint")
                
                with Horizontal(id="list-buttons"):
                    yield Button("Configurar Ahora", variant="primary", id="btn-config-now")
                    yield Button("Cerrar", variant="default", id="btn-close-list")

    def check_status(self, provider_id: str, env_var: str | None) -> tuple[bool, str]:
        if provider_id == "ollama":
            return True, "local"
        
        if KEYRING_AVAILABLE:
            try:
                key = keyring.get_password("ovandocode", provider_id)
                if key:
                    return True, "keyring"
            except Exception:
                pass
        
        if env_var:
            if os.getenv(env_var):
                return True, "env_sistema"
            
            env_path = Path.home() / ".ovandocode" / ".env"
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith(f"{env_var}="):
                            return True, ".env local"
        
        return False, ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-list":
            self.dismiss(False)
        elif event.button.id == "btn-config-now":
            self.action_configure()

    def on_static_clicked(self, event: Static.Clicked) -> None:
        if event.static.name:
            self.app.push_screen(CredentialsScreen(provider=event.static.name))

    def action_close(self) -> None:
        self.dismiss(False)

    def action_configure(self) -> None:
        self.app.push_screen(CredentialsScreen())
'@

    Set-Content -Path $CredentialsFile -Value $PythonCode -Encoding UTF8
    Write-Host "[OK]" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    $Errors++
}

# 3. Actualizar __init__.py
Write-Host "Actualizando __init__.py..." -NoNewline
try {
    $InitContent = Get-Content $InitFile -Raw -Encoding UTF8
    if ($InitContent -notmatch "CredentialsScreen") {
        # Buscar la última línea de importación o definición y agregar la nuestra
        $NewImport = "from .credentials import CredentialsScreen, CredentialsListScreen`n"
        
        # Insertar después del primer bloque de imports si es posible, o al final antes de __all__
        if ($InitContent -match "__all__") {
            $InitContent = $InitContent -replace "__all__", "$NewImport`n__all__"
        } else {
            $InitContent += "`n$NewImport"
        }
        
        Set-Content -Path $InitFile -Value $InitContent -Encoding UTF8
        Write-Host "[OK] Imports agregados." -ForegroundColor Green
    } else {
        Write-Host "[OK] Ya estaba actualizado." -ForegroundColor Gray
    }
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    $Errors++
}

# 4. Actualizar app.py (Comandos Slash)
Write-Host "Actualizando app.py (comandos slash)..." -NoNewline
try {
    $AppContent = Get-Content $AppFile -Raw -Encoding UTF8
    
    # Patrón seguro usando here-string para la búsqueda
    $HelpPattern = @'
if command == "help":
'@

    if ($AppContent -match [regex]::Escape($HelpPattern)) {
        $NewCommand = @'
        elif command == "credentials":
            args = parts[1:]
            if args and args[0] == "config":
                self.push_screen(CredentialsScreen())
            else:
                self.push_screen(CredentialsListScreen())
            return
'@
        # Insertar justo antes del bloque help
        $AppContent = $AppContent -replace ([regex]::Escape($HelpPattern)), "$NewCommand`n$HelpPattern"
        
        # Asegurar importación
        if ($AppContent -notmatch "from.*widgets.*import.*Credentials") {
            $AppContent = $AppContent -replace "from .*widgets import", "from .widgets import CredentialsScreen, CredentialsListScreen,"
        }
        
        Set-Content -Path $AppFile -Value $AppContent -Encoding UTF8
        Write-Host "[OK] Comando slash agregado." -ForegroundColor Green
    } else {
        Write-Host "[WARN] No se encontró el patrón 'help', revisión manual requerida." -ForegroundColor Yellow
        $Errors++
    }
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    $Errors++
}

# 5. Actualizar theme.tcss
Write-Host "Actualizando theme.tcss (estilos)..." -NoNewline
try {
    $ThemeContent = Get-Content $ThemeFile -Raw -Encoding UTF8
    if ($ThemeContent -notmatch "#creds-modal") {
        $NewStyles = @'

/* Credenciales Modales */
#creds-modal, #creds-list-modal {
    align: center middle;
    width: 60%;
    height: auto;
    max-height: 80%;
    background: $surface;
    border: thick $primary;
    padding: 1 2;
}

#creds-content, #creds-list-content {
    width: 100%;
    height: auto;
}

#creds-title, #list-title {
    text-align: center;
    text-style: bold;
    color: $text;
    margin-bottom: 1;
}

#provider-row, #creds-buttons, #list-buttons {
    width: 100%;
    height: auto;
    align: center middle;
    margin-top: 1;
}

#api-key-input {
    width: 100%;
    margin-top: 1;
}

.provider-item-configured {
    background: $success 20%;
    color: $text;
    padding: 1;
    margin: 1 0;
}

.provider-item-missing {
    background: $error 20%;
    color: $text;
    padding: 1;
    margin: 1 0;
}

#list-hint {
    text-align: center;
    color: $text-muted;
    margin-top: 1;
}
'@
        $ThemeContent += $NewStyles
        Set-Content -Path $ThemeFile -Value $ThemeContent -Encoding UTF8
        Write-Host "[OK] Estilos agregados." -ForegroundColor Green
    } else {
        Write-Host "[OK] Estilos ya existentes." -ForegroundColor Gray
    }
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    $Errors++
}

# ==========================================
# SECCIÓN DE VERIFICACIÓN FINAL
# ==========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Verificando Instalación             " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$CheckPassed = $true

# Check 1: Archivo credentials.py existe y tiene contenido
if ((Test-Path $CredentialsFile) -and ((Get-Item $CredentialsFile).Length -gt 1000)) {
    Write-Host "[PASS] credentials.py existe y tiene tamaño válido." -ForegroundColor Green
} else {
    Write-Host "[FAIL] credentials.py falta o está vacío." -ForegroundColor Red
    $CheckPassed = $false
}

# Check 2: __init__.py exporta las clases
$InitCheck = Get-Content $InitFile -Raw
if ($InitCheck -match "CredentialsScreen") {
    Write-Host "[PASS] __init__.py exporta CredentialsScreen." -ForegroundColor Green
} else {
    Write-Host "[FAIL] __init__.py no exporta CredentialsScreen." -ForegroundColor Red
    $CheckPassed = $false
}

# Check 3: app.py tiene el comando slash
$AppCheck = Get-Content $AppFile -Raw
if ($AppCheck -match 'command == "credentials"') {
    Write-Host "[PASS] app.py incluye el comando /credentials." -ForegroundColor Green
} else {
    Write-Host "[FAIL] app.py NO incluye el comando /credentials." -ForegroundColor Red
    $CheckPassed = $false
}

# Check 4: theme.tcss tiene estilos
$ThemeCheck = Get-Content $ThemeFile -Raw
if ($ThemeCheck -match "#creds-modal") {
    Write-Host "[PASS] theme.tcss incluye estilos de credenciales." -ForegroundColor Green
} else {
    Write-Host "[FAIL] theme.tcss NO incluye estilos." -ForegroundColor Red
    $CheckPassed = $false
}

Write-Host "`n========================================" -ForegroundColor Cyan
if ($CheckPassed -and ($Errors -eq 0)) {
    Write-Host "  ¡MIGRACIÓN EXITOSA!               " -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Siguientes pasos:" -ForegroundColor Yellow
    Write-Host "1. Ejecuta: pip install -e ." -ForegroundColor White
    Write-Host "2. Ejecuta: ovandocode" -ForegroundColor White
    Write-Host "3. Prueba escribiendo: /credentials" -ForegroundColor White
} else {
    Write-Host "  MIGRACIÓN COMPLETADA CON ERRORES  " -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Revisa los mensajes de error arriba." -ForegroundColor Yellow
    Write-Host "Es posible que debas ajustar manualmente app.py si el patrón 'help' cambió." -ForegroundColor Yellow
}