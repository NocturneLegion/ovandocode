---
name: commit-message
description: Redactar mensajes de commit en formato Conventional Commits
when_to_use: Cuando el usuario pida hacer commit, redactar mensajes de commit, o revisar cambios pendientes
tags: [git, commit, conventional-commits]
version: 1.0.0
author: OvandoCode
---

# Mensajes de commit (Conventional Commits)

## Formato

    <tipo>(<scope>): <descripcion corta>

    <cuerpo opcional explicando el que y el por que>

    <footer opcional: BREAKING CHANGE, Closes #123>

## Tipos permitidos
- feat: nueva funcionalidad
- fix: correccion de bug
- docs: solo documentacion
- style: formato, espacios (sin cambio de comportamiento)
- refactor: reestructuracion sin cambio funcional
- perf: mejora de performance
- test: agregar o corregir tests
- build: build system, dependencias
- ci: CI/CD
- chore: mantenimiento (no src, no tests)
- revert: revertir commit previo

## Reglas
1. Primera linea <= 72 caracteres.
2. Imperativo presente: "add" no "added" ni "adds".
3. Sin punto final en la primera linea.
4. Scope entre parentesis cuando aplique: feat(agent): ...
5. BREAKING CHANGE en el footer si rompe compatibilidad.

## Flujo
1. git status para ver cambios.
2. git diff --stat para resumen.
3. git diff (o --staged) para detalle.
4. git log --oneline -10 para ver estilo del repo.
5. Propone un mensaje.
6. Si el usuario aprueba, ejecuta: git add -A; git commit -m "<mensaje>".

## Ejemplos
- feat(tools): add grep tool with regex and glob filters
- fix(agent): handle provider timeout without crashing
- refactor(providers): extract openai_compat base class
- docs(readme): add installation instructions for Windows
