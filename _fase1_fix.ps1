# ============================================================
#  OVANDOCODE - FASE 1 v2 (recovery)
#  Guardar como: D:\Trabajo\OvandoCode\_fase1_fix.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 1 v2 (recovery) ===" -ForegroundColor Cyan

# --- 1. Eliminar pyproject.toml corrupto ---
Remove-Item 'pyproject.toml' -Force -ErrorAction SilentlyContinue

# --- 2. pyproject.toml (sin BOM) ---
$pyproject = @'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ovandocode"
version = "0.1.0"
description = "OVANDOCODE - Agente de codificacion autonomo"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "OvandoCode" }]
keywords = ["ai", "agent", "coding", "tui", "mcp", "llm"]

dependencies = [
    "textual>=0.83.0",
    "rich>=13.7.0",
    "typer>=0.12.0",
    "httpx>=0.27.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "keyring>=25.2.0",
    "python-dotenv>=1.0.1",
    "mcp>=1.0.0",
    "pyyaml>=6.0.2",
    "jinja2>=3.1.4",
    "aiofiles>=24.1.0",
    "tomli-w>=1.0.0",
    "platformdirs>=4.2.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.6.0",
]

[project.scripts]
ovandocode = "ovandocode.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/ovandocode"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src"]
'@
[IO.File]::WriteAllText("$ProjectRoot\pyproject.toml", $pyproject, $utf8)
Write-Host "[OK] pyproject.toml" -ForegroundColor Green

# --- 3. README.md ---
$readme = @'
# OVANDOCODE

Agente de codificacion autonomo para terminal.
TUI moderna, multi-proveedor LLM, MCP, skills y ejecucion segura de shell.

## Requisitos

- Python 3.11+
- Windows 10/11 (compatible con Linux/macOS)

## Instalacion (dev)

    uv sync --extra dev
    uv run ovandocode --help

## Uso

    ovandocode                    # TUI interactiva
    ovandocode "refactoriza ..."  # one-shot
    ovandocode --headless "..."   # headless

## Licencia

MIT
'@
[IO.File]::WriteAllText("$ProjectRoot\README.md", $readme, $utf8)
Write-Host "[OK] README.md" -ForegroundColor Green

# --- 4. __init__.py de subpaquetes ---
$subpkgs = @('config','providers','core','tools','skills','mcp','permissions','tui','tui\widgets')
foreach ($p in $subpkgs) {
    $full = "$ProjectRoot\src\ovandocode\$p\__init__.py"
    if (-not (Test-Path $full)) { [IO.File]::WriteAllText($full, '', $utf8) }
}
[IO.File]::WriteAllText("$ProjectRoot\src\ovandocode\__init__.py", '__version__ = "0.1.0"', $utf8)
Write-Host "[OK] __init__.py de subpaquetes" -ForegroundColor Green

# --- 5. __main__.py ---
$main = @'
"""OVANDOCODE - entrypoint para `python -m ovandocode`."""
from ovandocode.cli import main

if __name__ == "__main__":
    main()
'@
[IO.File]::WriteAllText("$ProjectRoot\src\ovandocode\__main__.py", $main, $utf8)

# --- 6. cli.py (placeholder de Fase 1) ---
$cli = @'
"""OVANDOCODE - CLI temporal (se reemplaza en Fase 10)."""
import typer

def main() -> None:
    typer.echo("OVANDOCODE - bootstrap OK (Fase 1)")

if __name__ == "__main__":
    main()
'@
[IO.File]::WriteAllText("$ProjectRoot\src\ovandocode\cli.py", $cli, $utf8)
Write-Host "[OK] __main__.py y cli.py" -ForegroundColor Green

# --- 7. tests + gitkeep ---
[IO.File]::WriteAllText("$ProjectRoot\tests\__init__.py", '', $utf8)
[IO.File]::WriteAllText("$ProjectRoot\sessions\.gitkeep", '', $utf8)
[IO.File]::WriteAllText("$ProjectRoot\logs\.gitkeep", '', $utf8)
[IO.File]::WriteAllText("$ProjectRoot\skills\.gitkeep", '', $utf8)
Write-Host "[OK] archivos auxiliares" -ForegroundColor Green

# --- 8. Reescribir .gitignore y .env.example sin BOM ---
$gitignore = @'
# Python
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.venv/
.python-version

# uv
uv.lock

# Env & secrets
.env
.env.local

# Sesiones y logs
sessions/*
!sessions/.gitkeep
logs/*
!logs/.gitkeep

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
'@
[IO.File]::WriteAllText("$ProjectRoot\.gitignore", $gitignore, $utf8)

$envexample = @'
# OVANDOCODE - variables de entorno (ejemplo)
# Copia a .env y completa tus claves

OPENROUTER_API_KEY=
OVANDOCODE_DEFAULT_MODEL=anthropic/claude-sonnet-4

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
GROQ_API_KEY=
MISTRAL_API_KEY=
XAI_API_KEY=

OLLAMA_BASE_URL=http://localhost:11434
LMSTUDIO_BASE_URL=http://localhost:1234/v1

OVANDOCODE_LOG_LEVEL=INFO
OVANDOCODE_PERMISSION_MODE=allowlist
'@
[IO.File]::WriteAllText("$ProjectRoot\.env.example", $envexample, $utf8)
Write-Host "[OK] .gitignore y .env.example" -ForegroundColor Green

# --- 9. uv sync ---
Write-Host "`n-> uv sync --extra dev (puede tardar 1-2 min)..." -ForegroundColor Yellow
uv sync --extra dev

# --- 10. Commit inicial ---
Write-Host "`n-> commit inicial..." -ForegroundColor Yellow
git add .
git commit -m "Fase 1: estructura base del proyecto OvandoCode" | Out-Null

# --- 11. Verificacion ---
Write-Host "`n=== Verificacion Fase 1 ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'pyproject.toml'          = (Test-Path 'pyproject.toml')
    'README.md'               = (Test-Path 'README.md')
    'src/ovandocode/cli.py'   = (Test-Path 'src\ovandocode\cli.py')
    'src/ovandocode/__main__.py' = (Test-Path 'src\ovandocode\__main__.py')
    '.venv/Scripts/python.exe'= (Test-Path '.venv\Scripts\python.exe')
    'textual instalado'       = [bool](uv pip list 2>$null | Select-String '^textual ')
    'typer instalado'         = [bool](uv pip list 2>$null | Select-String '^typer ')
    'mcp instalado'           = [bool](uv pip list 2>$null | Select-String '^mcp ')
    'commit inicial'          = [bool](git log --oneline 2>$null)
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 1 v2 completada." -ForegroundColor Cyan