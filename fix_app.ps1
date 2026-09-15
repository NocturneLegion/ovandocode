$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Trabajo\OvandoCode"
$AppFile = Join-Path $ProjectRoot "src\ovandocode\tui\app.py"
$BackupFile = Join-Path $ProjectRoot "src\ovandocode\tui\app.py.bak"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Reparando integración en app.py" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path $AppFile)) {
    Write-Host "[ERROR] No se encuentra app.py" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Creando backup..." -ForegroundColor Yellow
Copy-Item $AppFile $BackupFile

$Content = Get-Content $AppFile -Raw -Encoding UTF8

# Definimos el código Python a insertar usando comillas simples para evitar conflictos
$PythonCode = @'

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
            self.query_one("#chat-history", RichLog).clear()
            self.notify("Historial limpiado")
        elif cmd == "credentials":
            from .widgets.credentials import CredentialsListScreen, CredentialsScreen
            if args.lower() == "config":
                self.push_screen(CredentialsScreen())
            else:
                self.push_screen(CredentialsListScreen())
        else:
            self.notify(f"Comando desconocido: {cmd}", severity="warning")
'@

# Verificamos si ya existe el comando credentials
if ($Content -like "*elif cmd == `"credentials`"*") {
    Write-Host "[SKIP] El comando /credentials ya existe." -ForegroundColor Green
} else {
    Write-Host "[INFO] Insertando código de comandos..." -ForegroundColor Yellow
    # Añadimos el código al final del archivo
    $Content += "`n" + $PythonCode
    Set-Content -Path $AppFile -Value $Content -Encoding UTF8 -NoNewline
    Write-Host "[OK] Código insertado." -ForegroundColor Green
}

# VERIFICACIÓN FINAL
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Verificando Resultados" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$FinalContent = Get-Content $AppFile -Raw -Encoding UTF8

if ($FinalContent -like "*credentials*") {
    Write-Host "[PASS] El comando /credentials está presente en app.py." -ForegroundColor Green
    Write-Host "`n[EXITO] Migración completada." -ForegroundColor Green
    Write-Host "Ejecuta ahora: pip install -e ." -ForegroundColor Cyan
} else {
    Write-Host "[FAIL] No se detectó el comando. Restaurando backup..." -ForegroundColor Red
    Copy-Item $BackupFile $AppFile -Force
    Write-Host "Backup restaurado. Revisa manualmente." -ForegroundColor Yellow
}