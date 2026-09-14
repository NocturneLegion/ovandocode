# Skills

Las **skills** son documentos markdown que le enseñan al agente cómo hacer tareas específicas. Cuando el agente detecta que la tarea encaja con una skill, la carga y sigue sus instrucciones.

Es como darle al agente un manual de procedimiento para cada tipo de trabajo.

---

## Concepto

Una skill es una carpeta con un archivo `SKILL.md`:

```
skills/
└── mi-skill/
    └── SKILL.md
```

El `SKILL.md` tiene:

1. **Frontmatter YAML** con metadata (nombre, descripción, cuándo usar).
2. **Cuerpo markdown** con las instrucciones detalladas.

---

## Estructura de un SKILL.md

```markdown
---
name: mi-skill
description: Descripcion breve de que hace esta skill
when_to_use: Cuando el usuario pida X, Y o Z
tags: [python, testing, tdd]
version: 1.0.0
author: Tu Nombre
---

# Titulo de la skill

## Instrucciones paso a paso

1. Hacer esto
2. Hacer aquello
3. Verificar el resultado

## Ejemplos

(aqui van bloques de codigo con triple-backtick)

## Errores comunes

- Error 1: como solucionarlo
- Error 2: como solucionarlo
```

### Campos del frontmatter

| Campo | Requerido | Descripción |
|---|---|---|
| `name` | Sí | Identificador único (snake-case o kebab-case) |
| `description` | Sí | Descripción de una línea que ve el LLM en el catálogo |
| `when_to_use` | Recomendado | Cuándo debe cargarse la skill |
| `tags` | Opcional | Array de strings para búsqueda |
| `version` | Opcional | Versión semántica |
| `author` | Opcional | Nombre del autor |

---

## Ubicaciones

OVANDOCODE busca skills en 3 ubicaciones, en orden de prioridad (mayor gana):

| Prioridad | Ubicación | Uso |
|---|---|---|
| 1 (mayor) | `<proyecto>/skills/` | Skills específicas del proyecto actual |
| 2 | `~/.ovandocode/skills/` | Skills del usuario (compartidas entre proyectos) |
| 3 (menor) | `src/ovandocode/skills/builtin/` | Skills incluidas con OVANDOCODE |

Si dos skills tienen el mismo `name`, gana la de mayor prioridad.

---

## Skills incluidas

OVANDOCODE viene con 3 skills built-in:

### `python-testing`

Cómo escribir tests con pytest siguiendo buenas prácticas. Se activa cuando pides escribir, arreglar o revisar tests.

Incluye:

- Estructura recomendada de tests (`tests/` paralelo a `src/`)
- Reglas de estilo (un assert por test, fixtures, parametrize)
- Plantillas de código
- Comandos de pytest útiles
- Flujo de trabajo completo

### `code-review`

Checklist de 10 puntos para revisar código. Se activa cuando pides revisar, auditar o mejorar código.

Incluye:

- Corrección, manejo de errores, recursos, tipos, duplicación...
- Formato de salida por severidad (críticos / importantes / menores)
- Reglas para no modificar sin permiso

### `commit-message`

Cómo redactar mensajes de commit en formato Conventional Commits. Se activa cuando pides hacer commits.

Incluye:

- Formato completo (tipo, scope, descripción, cuerpo, footer)
- Lista de tipos permitidos (`feat`, `fix`, `docs`, `refactor`, ...)
- Reglas (imperativo presente, 72 chars, etc.)
- Ejemplos

---

## Comandos CLI

### Listar skills disponibles

```powershell
ovandocode skills list
```

Salida:

```
== 3 skill(s) ==
  [builtin ] code-review          v1.0.0   Revisar codigo en busca de bugs...
  [builtin ] commit-message       v1.0.0   Redactar mensajes de commit...
  [builtin ] python-testing       v1.0.0   Escribir y ejecutar tests...
```

### Ver una skill completa

```powershell
ovandocode skills show python-testing
```

### Crear una skill nueva

```powershell
ovandocode skills init mi-skill
```

Esto crea `skills/mi-skill/SKILL.md` con un template inicial. Edítalo con:

```powershell
notepad "D:\Trabajo\OvandoCode\skills\mi-skill\SKILL.md"
```

---

## Ejemplo completo: skill de deployment

Supongamos que quieres que el agente sepa cómo desplegar tu app a producción.

### 1. Crear la skill

```powershell
ovandocode skills init deploy-prod
```

### 2. Editar `skills/deploy-prod/SKILL.md`

```markdown
---
name: deploy-prod
description: Desplegar la aplicacion a produccion con validaciones previas
when_to_use: Cuando el usuario pida desplegar a produccion, publicar, o subir cambios al servidor
tags: [deploy, production, ci-cd]
version: 1.0.0
---

# Deploy a produccion

## Pre-requisitos (verificar SIEMPRE antes de desplegar)

1. Tests pasando: `uv run pytest`
2. Sin cambios sin commitear: `git status` debe estar limpio
3. Rama actual es main: `git branch --show-current`
4. Ultimo commit tiene tag: `git describe --tags`

## Pasos

1. Ejecutar `uv run pytest` y confirmar 100% verde.
2. Ejecutar `git pull origin main` para traer cambios.
3. Ejecutar `git push origin main`.
4. Ejecutar el script de deploy: `./scripts/deploy.ps1`.
5. Verificar el endpoint de health: `curl https://api.example.com/health`.
6. Confirmar que devuelve `{`status`:`ok`}`.

## Rollback

Si algo falla:

1. `git revert HEAD` y push.
2. Ejecutar `./scripts/deploy.ps1` de nuevo.

## Errores comunes

- **Tests fallan**: no desplegar, arreglar primero.
- **Health check falla**: rollback inmediato.
- **Permiso denegado en deploy.ps1**: verificar que tienes rol de admin.
```

### 3. Uso

Cuando le pidas al agente: *"despliega a producción"*, detectará la skill y ejecutará el procedimiento.

```powershell
ovandocode run "Despliega la app a produccion"
```

El agente:

1. Ve la skill `deploy-prod` en el catálogo del system prompt.
2. Detecta que la tarea encaja con `when_to_use`.
3. Llama a `load_skill(name="deploy-prod")`.
4. Sigue las instrucciones paso a paso.

---

## Cómo funciona internamente

1. **Al arrancar una sesión**, el agente escanea las 3 ubicaciones y construye un **catálogo** con `name` + `description` de cada skill.
2. Ese catálogo se inyecta al final del **system prompt**.
3. Cuando el LLM ve la tarea, si alguna skill encaja, llama a `load_skill`.
4. La tool devuelve el **cuerpo completo** de la skill (markdown con instrucciones).
5. El LLM sigue las instrucciones con las tools que ya tiene.

Por eso las skills son **baratas**: solo se cargan cuando hacen falta. El resto del tiempo, solo ocupan su descripción (1 línea).

---

## Buenas prácticas al escribir skills

### 1. Descripción clara y concisa

Bien: `description: Escribir tests de Python con pytest`

Mal: `description: Esta skill te ayuda a escribir tests de Python con pytest cuando lo necesites`

### 2. when_to_use específico

Bien: `when_to_use: Cuando el usuario pida escribir, corregir o revisar tests`

Mal: `when_to_use: Cuando sea util`

### 3. Instrucciones accionables

Cada paso debe ser algo concreto que el agente pueda ejecutar con una tool.

### 4. Incluye verificaciones

El agente debe saber cómo confirmar que hizo bien el trabajo (correr tests, verificar outputs, etc.).

### 5. Documenta errores comunes

Ahorra tiempo cuando el agente encuentre problemas.

### 6. Usa ejemplos concretos

Un ejemplo de código vale más que 10 líneas de prosa.

---

## Compartir skills con la comunidad

Puedes publicar tus skills como repos independientes. La estructura:

```
mi-skill-pack/
├── README.md
├── skills/
│   ├── skill-1/SKILL.md
│   ├── skill-2/SKILL.md
│   └── skill-3/SKILL.md
└── LICENSE
```

Para instalarlas, el usuario copia `skills/*` a su carpeta `~/.ovandocode/skills/`.

---

## Troubleshooting

### La skill no aparece en `skills list`

**Causas**:

1. El archivo no se llama exactamente `SKILL.md` (case-sensitive).
2. El frontmatter no empieza con `---` en la primera línea.
3. Falta el campo `description`.

Corre `ovandocode skills list` y revisa la sección de errores.

### El agente no carga la skill aunque encaje

**Causas**:

1. El `when_to_use` no es claro.
2. El modelo es débil para tool calling.
3. Hay demasiadas skills y el catálogo se diluye.

**Solución**: sé explícito en el prompt (`"Usa la skill X para..."`) o simplifica el `when_to_use`.

### El YAML del frontmatter falla

Verifica con un parser YAML online: https://yaml-online-parser.appspot.com/

Errores comunes:

- Tags con caracteres especiales sin comillas: `tags: [mi-tag, otro-tag]`
- Dos puntos dentro de un valor: `description: "Texto: con dos puntos"`
- Indentación inconsistente

---

## Siguiente paso

- [MCP](mcp.md) — servidores MCP externos
- [Interfaz](interfaz.md) — TUI y CLI
- [Solución de problemas](troubleshooting.md)
