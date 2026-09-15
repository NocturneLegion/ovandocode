$ErrorActionPreference = "Stop"
$AppFile = "D:\Trabajo\OvandoCode\src\ovandocode\tui\app.py"
$BackupFile = "D:\Trabajo\OvandoCode\src\ovandocode\tui\app.py.backup"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Reparación Definitiva de app.py" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Crear Backup
Copy-Item $AppFile $BackupFile -Force
Write-Host "[OK] Backup creado." -ForegroundColor Green

# 2. Leer todo el archivo
$Lines = Get-Content $AppFile
$NewLines = @()
$InBadBlock = $false
$FoundFuture = $false
$SkipUntilDef = $false

# Identificar y eliminar el bloque mal insertado al inicio
# Buscamos desde la línea 4 hasta que encontremos una definición de clase o método válido
for ($i = 0; $i -lt $Lines.Count; $i++) {
    $Line = $Lines[$i]
    
    # Si es una de las primeras líneas (imports), la mantenemos
    if ($i -lt 3) {
        $NewLines += $Line
        continue
    }

    # Detectar si estamos en el bloque basura insertado anteriormente
    # El bloque basura suele empezar con 'def on_mount' o código suelto antes de la clase
    if ($Line -match "^from __future__" -and $i -gt 2) {
        # Si hay otro from __future__ después de la línea 3, es error. Lo saltamos.
        continue
    }

    # Si encontramos el inicio de la clase principal, paramos de saltar
    if ($Line -match "^class OvandoCodeApp") {
        $SkipUntilDef = $false
        $NewLines += $Line
        continue
    }

    # Si aún no hemos encontrado la clase y la línea parece código suelto (def, import, etc)
    # Y estamos después de los imports iniciales, probablemente sea basura del script anterior
    if (-not $SkipUntilDef) {
        if ($Line -match "^def " -or $Line -match "^from " -or $Line -match "^import ") {
             # Verificar si es parte de los imports válidos iniciales o basura
             # Asumimos que todo después de la línea 3 que NO sea la clase es basura hasta encontrar la clase
             continue 
        }
    }
}

# Re-leer el archivo limpio temporalmente en memoria para la siguiente fase
# (En realidad, vamos a reconstruir el archivo desde cero con la lógica correcta)

# ESTRATEGIA ROBUSTA:
# 1. Leer el archivo original (backup)
# 2. Encontrar la última línea de la clase OvandoCodeApp
# 3. Insertar nuestro código ahí

$OriginalContent = Get-Content $BackupFile -Raw -Encoding UTF8
$OutputContent = ""

# Definir el código Python CORRECTO (indentado con 4 espacios para estar dentro de la clase)
$PythonCode = @"

    def on_mount(self) -> None:
        """Configurar la interfaz al iniciar."""
        self.query_one("#command-input", Input).focus()

    async def handle_command(self, command: str) -> None:
        """Procesa comandos slash como /credentials."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            self.notify("Comandos: /help, /clear, /credentials, /credentials config")
        elif cmd == "clear":
            self.query_one("#chat-history", RichLog).clear()
            self.notify("Historial limpiado")
        elif cmd == "credentials":
            try:
                from .widgets.credentials import CredentialsListScreen, CredentialsScreen
                if args.lower() == "config":
                    self.push_screen(CredentialsScreen())
                else:
                    self.push_screen(CredentialsListScreen())
            except Exception as e:
                self.notify(f"Error cargando credenciales: {e}", severity="error")
        else:
            self.notify(f"Comando desconocido: {cmd}", severity="warning")
"@

# Lógica de reconstrucción
$AllLines = Get-Content $BackupFile
$FinalLines = @()
$ClassStarted = $false
$LastClassLineIndex = -1
$IndentCount = 0

# Primero, limpiar las líneas basura del inicio si existen en el backup (por si el backup ya estaba sucio)
# Asumimos que el backup generado por el script anterior tiene el error.
# Vamos a filtrar manualmente las líneas problemáticas conocidas.

$CleanLines = @()
$SkipHeaderGarbage = $false

for ($i = 0; $i -lt $AllLines.Count; $i++) {
    $L = $AllLines[$i]
    
    # Saltar líneas específicas que sabemos que rompen el archivo si están en las posiciones incorrectas
    if ($i -gt 3 -and $i -lt 60) {
        if ($L -match "^def on_mount" -or $L -match "^async def handle_command" -or $L -match "^    def on_mount") {
            # Si es una definición de función SUelta antes de la clase, la marcamos para saltar
            # Pero cuidado, necesitamos saber si estamos DENTRO o FUERA de la clase.
            # La forma más segura es reconstruir solo lo necesario.
        }
    }
    $CleanLines += $L
}

# Mejor enfoque: Usar Regex para encontrar la clase e inyectar al final de ella.
# Pero primero asegurémonos de que el archivo de entrada esté limpio de la inserción anterior.
# Si el backup tiene el error "from __future__" en la línea 3, debemos limpiarlo.

$TempLines = Get-Content $BackupFile
$SafeLines = @()
$FoundFirstClass = $false
$GarbageEnded = $false

for ($i = 0; $i -lt $TempLines.Count; $i++) {
    $CurrentLine = $TempLines[$i]
    
    # Si es una de las 3 primeras líneas, mantener siempre (imports)
    if ($i -le 2) {
        $SafeLines += $CurrentLine
        continue
    }

    # Si ya encontramos la clase, mantener todo desde ahí
    if ($FoundFirstClass) {
        $SafeLines += $CurrentLine
        continue
    }

    # Si estamos entre la línea 3 y el inicio de la clase, verificar si es basura
    if ($CurrentLine -match "^class OvandoCodeApp") {
        $FoundFirstClass = $true
        $SafeLines += $CurrentLine
        continue
    }

    # Si no es la clase y estamos en la zona peligrosa, omitir si parece código python suelto
    # Esto elimina la inserción erronea del script anterior
    if ($CurrentLine -match "^def " -or $CurrentLine -match "^from " -or $CurrentLine -match "^import " -or $CurrentLine -match '^\s+"""') {
        # Omitir esta línea (es la basura insertada)
        continue
    }
    
    # Si es una línea vacía o comentario genérico antes de la clase, también la omitimos para limpiar
    if ([string]::IsNullOrWhiteSpace($CurrentLine) -or $CurrentLine.TrimStart().StartsWith("#")) {
        continue
    }
}

# Ahora $SafeLines tiene el archivo limpio hasta el inicio de la clase.
# Necesitamos encontrar el FINAL de la clase para insertar nuestros métodos.
# Como Python se basa en indentación, buscamos la última línea que tenga indentación de clase (4 o 8 espacios)
# antes de que el archivo termine o haya otra clase de nivel superior.

$FinalOutput = @()
$MaxIndex = $SafeLines.Count - 1
$InsertionPoint = -1

# Recorrer hacia atrás desde el final para encontrar dónde termina la clase OvandoCodeApp
for ($i = $MaxIndex; $i -ge 0; $i--) {
    $L = $SafeLines[$i]
    if ($L -match "^class OvandoCodeApp") {
        # Encontramos el inicio, el punto de inserción es justo antes de esto? No, queremos al final.
        # El punto de inserción será después de la última línea indentada perteneciente a esta clase.
        break
    }
    
    # Si la línea tiene indentación (empieza con espacios), es candidata a ser el final de la clase
    if ($L -match "^\s+") {
        $InsertionPoint = $i
        break
    }
}

# Construir el archivo final
for ($i = 0; $i -le $MaxIndex; $i++) {
    $FinalOutput += $SafeLines[$i]
    
    # Si llegamos al punto de inserción (la última línea indentada encontrada)
    if ($i -eq $InsertionPoint) {
        # Agregar una línea vacía y luego nuestro código
        $FinalOutput += ""
        # Dividir el código Python en líneas y agregarlas
        $PythonCode -split "`n" | ForEach-Object { $FinalOutput += $_ }
    }
}

# Escribir el archivo corregido
Set-Content -Path $AppFile -Value $FinalOutput -Encoding UTF8 -NoNewline

Write-Host "[OK] Archivo reconstruido y código insertado correctamente." -ForegroundColor Green

# 3. Verificación
Write-Host "`nVerificando..." -ForegroundColor Yellow
$FinalCheck = Get-Content $AppFile -Raw
if ($FinalCheck -match "def handle_command.*credentials") {
    Write-Host "[PASS] Integración exitosa." -ForegroundColor Green
    Write-Host "`nLISTO. Ejecuta: pip install -e ." -ForegroundColor Cyan
} else {
    Write-Host "[FAIL] Algo salió mal. Revisa el archivo manualmente." -ForegroundColor Red