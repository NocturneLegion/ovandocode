# Instalación

Esta guía cubre la instalación de OVANDOCODE desde cero en Windows, Linux y macOS.

---

## Requisitos

### Mínimos

| Componente | Versión | Notas |
|---|---|---|
| **Python** | 3.11 o superior | Requerido por tomllib, StrEnum y typing moderno |
| **uv** | última | Gestor de paquetes y entornos de Astral |
| **Git** | 2.30+ | Solo para desarrollo o para clonar el repo |
| **Sistema** | Windows 10/11, Linux (glibc 2.28+), macOS 12+ | |

### Recomendados

| Componente | Por qué |
|---|---|
| **PowerShell 7+** (pwsh) | Mejor rendimiento que Windows PowerShell 5.1, mejor compatibilidad con UTF-8 |
| **Windows Terminal** | Soporte completo de TUI (Textual funciona mejor aquí que en cmd.exe) |
| **Git Bash** o **WSL** | Para usar run_bash en Windows |

### Opcionales

- **Node.js 18+** si vas a usar servidores MCP escritos en JavaScript/TypeScript.
- **Docker** si vas a ejecutar MCP servers containerizados.

---

## 1. Instalar uv

uv es el gestor que usa OVANDOCODE para gestionar Python y dependencias. Es **extremadamente rápido** y aísla todo del sistema.

### Windows (PowerShell)

```powershell
Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
```

Se instala en `%USERPROFILE%\.local\bin\uv.exe`. Cierra y reabre la terminal para que el PATH se actualice.

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

O con Homebrew:

```bash
brew install uv
```

### Verificar

```powershell
uv --version
# uv 0.5.x o superior
```

---

## 2. Instalar OVANDOCODE

Tienes dos opciones:

### Opción A — Como comando global (recomendado)

Instala ovandocode como herramienta independiente en ~/.local/bin. Disponible desde cualquier carpeta.

**Desde el repo local:**

```powershell
cd D:\Trabajo\OvandoCode
uv tool install --editable .
```

**Desde GitHub (una vez publicado):**

```powershell
uv tool install git+https://github.com/TU-USUARIO/ovandocode.git
```

**Verificar:**

```powershell
ovandocode --version
# OVANDOCODE v0.1.0
```

Si el comando no se encuentra, reinicia la terminal o ejecuta:

```powershell
uv tool update-shell
```

### Opción B — Solo para probar (sin instalar)

Clona el repo, sincroniza dependencias y ejecuta con uv run:

```powershell
git clone https://github.com/TU-USUARIO/ovandocode.git
cd ovandocode
uv sync --extra dev
uv run ovandocode --version
```

Todos los comandos requieren el prefijo uv run (ej: `uv run ovandocode chat`).

---

## 3. Instalador automático (Windows)

Si clonaste el repo, hay un script de instalación automática:

```powershell
cd D:\Trabajo\OvandoCode
.\install.ps1
```

Esto:

1. Instala uv si no lo tienes.
2. Ejecuta uv tool install --editable .
3. Verifica que el binario funciona.

---

## 4. Primer arranque

### Sin configuración (no funcionará todavía)

```powershell
ovandocode
```

Abrirá la TUI, pero el agente no podrá usar ningún proveedor hasta que configures una API key.

### Configurar un proveedor

Elige **una** de las opciones:

#### Opción rápida — Groq (gratis, muy rápido)

1. Regístrate en https://console.groq.com/keys
2. Copia tu key (empieza por gsk_).
3. Créala en el .env del proyecto:

```powershell
cd D:\Trabajo\OvandoCode
notepad .env
```

Contenido:

```env
GROQ_API_KEY=gsk_tu_key_aqui
OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
OVANDOCODE_MAX_TOKENS=4096
```

Guarda y cierra.

#### Opción recomendada — OpenRouter (muchos modelos)

1. Regístrate en https://openrouter.ai/keys
2. Copia tu key (empieza por sk-or-v1-).
3. Créala en .env:

```env
OPENROUTER_API_KEY=sk-or-v1-tu_key
OVANDOCODE_DEFAULT_PROVIDER=openrouter
OVANDOCODE_DEFAULT_MODEL=openrouter/free
OVANDOCODE_MAX_TOKENS=4096
```

#### Opción segura — Windows Credential Manager

Si prefieres no escribir la key en el .env:

```powershell
ovandocode config set-key groq
# Te pedirá la key (no se muestra mientras escribes)
```

Luego edita .env solo con el provider y modelo:

```env
OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
```

### Verificar configuración

```powershell
ovandocode config show
```

Salida esperada:

```
== OVANDOCODE config ==
  project_root     : D:\Trabajo\OvandoCode
  config_dir       : C:\Users\TU-USUARIO\AppData\Local\OvandoCode\OvandoCode
  logs_dir         : C:\Users\TU-USUARIO\AppData\Local\OvandoCode\OvandoCode\Logs
  default_provider : groq
  default_model    : openai/gpt-oss-120b
  permission_mode  : allowlist
  theme            : dark
  log_level        : INFO
```

```powershell
ovandocode config providers
```

Salida esperada (con al menos uno en OK):

```
== Proveedores ==
  [OK ] groq         source=env
  [-- ] openai       source=none
  [-- ] anthropic    source=none
  ...
```

### Primer chat

```powershell
ovandocode
```

Escribe dentro de la TUI:

```
Hola, ¿qué herramientas tienes?
```

Si el agente responde, todo funciona.

---

## 5. Instalación en Linux / macOS

Los comandos son los mismos, con dos diferencias:

1. uv tool install instala en ~/.local/bin/ovandocode (sin .exe).
2. run_powershell fallará si no tienes PowerShell Core instalado. Usa run_bash en su lugar.

Instalar PowerShell Core (opcional, para tener ambas shells):

```bash
# macOS
brew install powershell

# Ubuntu/Debian
sudo apt install powershell
```

---

## 6. Desinstalación

### Quitar el comando global

```powershell
uv tool uninstall ovandocode
```

### Borrar datos de usuario

Windows:

```powershell
Remove-Item "$env:LOCALAPPDATA\OvandoCode" -Recurse -Force
Remove-Item "$env:APPDATA\OvandoCode" -Recurse -Force
```

Linux / macOS:

```bash
rm -rf ~/.config/OvandoCode ~/.local/share/OvandoCode ~/.local/state/OvandoCode
```

### Borrar credenciales de keyring

```powershell
ovandocode config del-key groq
ovandocode config del-key openrouter
# ... para cada proveedor
```

---

## 7. Actualizar

### Si instalaste desde el repo local

```powershell
cd D:\Trabajo\OvandoCode
git pull
uv tool install --editable . --reinstall
```

### Si instalaste desde GitHub

```powershell
uv tool install --force git+https://github.com/TU-USUARIO/ovandocode.git
```

---

## Siguiente paso

- [Configuración](configuracion.html) — .env, config.toml, variables de entorno
- [Proveedores](proveedores.html) — cada proveedor LLM en detalle
- [Interfaz](interfaz.html) — TUI y CLI

---

[← Volver al inicio](index.html)
