# ============================================================
#  OVANDOCODE - FIX Fase 2: mover cli.py al lugar correcto
#  Guardar como: D:\Trabajo\OvandoCode\_fix_fase2.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== FIX Fase 2 ===" -ForegroundColor Cyan

$wrongCli  = "$ProjectRoot\src\ovandocode\ovandocode\cli.py"
$wrongDir  = "$ProjectRoot\src\ovandocode\ovandocode"
$rightCli  = "$ProjectRoot\src\ovandocode\cli.py"

# 1) Si existe el cli.py mal ubicado, movemos su contenido al lugar correcto
if (Test-Path $wrongCli) {
    Write-Host "-> Encontrado cli.py mal ubicado. Moviendo..." -ForegroundColor Yellow
    Move-Item -Path $wrongCli -Destination $rightCli -Force
}

# 2) Eliminar la carpeta duplicada (src/ovandocode/ovandocode) si quedo vacia o con residuos
if (Test-Path $wrongDir) {
    # Solo borrar si NO tiene archivos .py relevantes (excepto __init__.py vacio o ya movido)
    $leftover = Get-ChildItem $wrongDir -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -ne '__init__.py' }
    if (-not $leftover) {
        Remove-Item $wrongDir -Recurse -Force
        Write-Host "[OK] carpeta duplicada eliminada" -ForegroundColor Green
    } else {
        Write-Warning "La carpeta $wrongDir aun tiene archivos, revísala manualmente:"
        Get-ChildItem $wrongDir -Recurse | Format-Table FullName
    }
}

# 3) Verificar que ahora si este el cli.py correcto
if (-not (Test-Path $rightCli)) {
    Write-Host "[ERROR] No existe $rightCli" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] cli.py en: $rightCli" -ForegroundColor Green

# 4) Reinstalar el paquete en modo editable (por si uv cacheo la version anterior)
Write-Host "`n-> reinstalando paquete con uv sync..." -ForegroundColor Yellow
uv sync --extra dev

# 5) Pruebas
Write-Host "`n-> probando CLI..." -ForegroundColor Yellow
uv run ovandocode version
Write-Host ""
uv run ovandocode config show
Write-Host ""
uv run ovandocode config providers

# 6) Commit
Write-Host "`n-> commit fix..." -ForegroundColor Yellow
git add .
git commit -m "Fix Fase 2: mover cli.py a src/ovandocode/cli.py" | Out-Null

Write-Host "`n=== Verificacion ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'cli.py en ruta correcta'      = (Test-Path 'src\ovandocode\cli.py')
    'carpeta duplicada eliminada'  = -not (Test-Path 'src\ovandocode\ovandocode')
    'import ovandocode.config'     = (& { uv run python -c "import ovandocode.config" *> $null; $LASTEXITCODE -eq 0 })
    'version command'              = [bool](uv run ovandocode version 2>$null)
    'config show'                  = [bool](uv run ovandocode config show 2>$null)
    'config providers'             = [bool](uv run ovandocode config providers 2>$null)
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFix completado." -ForegroundColor Cyan