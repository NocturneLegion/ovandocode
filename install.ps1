# ============================================================
#  OVANDOCODE - Instalador para Windows
# ============================================================
$ErrorActionPreference = 'Stop'

Write-Host '=== OVANDOCODE :: Instalador ===' -ForegroundColor Cyan

# 1. Verificar uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host '-> Instalando uv...' -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

# 2. Instalar ovandocode como tool global
Write-Host '-> Instalando OVANDOCODE...' -ForegroundColor Yellow
uv tool install --editable .

# 3. Verificar
Write-Host ''
Write-Host '=== Verificacion ===' -ForegroundColor Cyan
$bin = "$env:USERPROFILE\.local\bin\ovandocode.exe"
if (Test-Path $bin) {
    Write-Host "[OK] ovandocode instalado en $bin" -ForegroundColor Green
    & $bin --version
} else {
    Write-Host '[!!] no se encontro el binario. Revisa la salida de uv.' -ForegroundColor Red
}

Write-Host ''
Write-Host 'Listo! Ejecuta: ovandocode --help' -ForegroundColor Cyan
Write-Host 'Si el comando no se encuentra, reinicia la terminal.' -ForegroundColor Yellow
