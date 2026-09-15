$ErrorActionPreference = "Stop"
$AppFile = "D:\Trabajo\OvandoCode\src\ovandocode\tui\app.py"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Corrigiendo estructura de app.py" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Leer todo el archivo
$Content = Get-Content $AppFile -Raw -Encoding UTF8

# Definir el bloque de código CORRECTO (Métodos de la clase)
$MethodsCode = @'

    def on_mount(self) -> None:
        """Configuración inicial."""
        try:
            self.query_one("#command-input", Input).focus()
        except Exception:
            pass

    async def handle_command(self, command: str) -> None:
        """Procesa comandos slash."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            self.notify("Comandos: /help, /clear, /credentials, /credentials config")
        elif cmd == "clear":
            try:
                self.query_one("#chat-history", RichLog).clear()
                self.notify("Historial limpiado")
            except Exception:
                pass
        elif cmd == "credentials":
            from .widgets.credentials import CredentialsListScreen, CredentialsScreen
            if args.lower() == "config":
                self.push_screen(CredentialsScreen())
            else:
                self.push_screen(CredentialsListScreen())
        else:
            self.notify(f"Comando desconocido: {cmd}", severity="warning")
'@

# 1. LIMPIEZA: Si el código se pegó mal al principio (causando el error), lo quitamos.
# Buscamos patrones que no deberían estar al inicio del archivo
if ($Content -match "def on_mount\(self\)") {
    # Verificamos si está antes de la primera definición de clase real
    $Lines = Get-Content $AppFile
    $CleanLines = @()
    $SkipBlock = $false
    $FoundClass = $false
    
    # Lógica simple: reconstruir el archivo sin los métodos duplicados al inicio
    # Pero para ser seguros, vamos a hacer una limpieza más drástica si detectamos el error específico
    
    # Estrategia: Vamos a leer línea por línea y eliminar cualquier 'def on_mount' o 'def handle_command' 
    # que aparezca ANTES de encontrar la línea 'class OvandoCodeApp'
    
    $InBadZone = $true
    $NewContentLines = @()
    
    foreach ($line in $Lines) {
        if ($line -match "^class OvandoCodeApp") {
            $InBadZone = $false
            $NewContentLines += $line
        } elseif ($InBadZone) {
            # Estamos en la zona prohibida (antes de la clase)
            # Si la línea es parte de nuestros métodos erróneos, la saltamos
            if ($line -match "def on_mount" -or $line -match "def handle_command" -or $line -match "elif cmd ==" -or $line -match "from .* credentials") {
                continue # Saltar esta línea
            }
            # Si es una línea vacía o comentario suelto al inicio, también podríamos saltarla, pero dejémosla por seguridad salvo que sea obvio
            if ($line.Trim() -eq "" -or $line.Trim().StartsWith("#")) {
                 # Mantener espacios vacíos iniciales si son necesarios, pero usualmente sobran aquí
                 continue
            }
            $NewContentLines += $line
        } else {
            $NewContentLines += $line
        }
    }
    
    # Actualizar contenido con la limpieza
    $Content = $NewContentLines -join "`n"
    Write-Host "[OK] Limpieza de código mal ubicado realizada." -ForegroundColor Green
}

# 2. INSERCIÓN: Ahora aseguramos que el código esté DENTRO de la clase al final.
# Verificamos si ya existe el método handle_command correctamente ubicado (después de 'class')
if ($Content -notmatch "elif cmd == \"credentials\":") {
    Write-Host "[INFO] Insertando métodos en la ubicación correcta..." -ForegroundColor Yellow
    
    # Encontrar la última línea de la clase (usualmente antes del último cierre o al final del archivo)
    # Añadimos el código al final del archivo, asumiendo que la indentación se manejará o que es el final de la clase.
    # Para Textual, los métodos pueden ir en cualquier orden dentro de la clase.
    
    # Asegurar salto de línea al final
    if (-not $Content.EndsWith("`n")) {
        $Content += "`n"
    }
    
    $Content += $MethodsCode
    $Content += "`n"
    
    Set-Content -Path $AppFile -Value $Content -Encoding UTF8 -NoNewline
    Write-Host "[OK] Métodos agregados al final del archivo." -ForegroundColor Green
} else {
    Write-Host "[SKIP] El comando /credentials ya parece estar implementado correctamente." -ForegroundColor Green
}

# 3. VERIFICACIÓN FINAL
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Validando Sintaxis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Intentar importar el módulo para ver si hay errores de sintaxis
try {
    # Cambiar temporalmente al directorio src para el test
    Push-Location "D:\Trabajo\OvandoCode\src"
    python -c "import ovandocode.tui.app" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] ¡Sintaxis correcta! El módulo importa sin errores." -ForegroundColor Green
        Write-Host "`n[EXITO] Todo listo. Ejecuta: pip install -e ." -ForegroundColor Cyan
    } else {
        Write-Host "[FAIL] Error de sintaxis persistente. Revisa app.py manualmente." -ForegroundColor Red
        python -c "import ovandocode.tui.app"
    }
    Pop-Location
} catch {
    Write-Host "[ERROR] Excepción al validar: $_" -ForegroundColor Red
}