---
name: code-review
description: Revisar codigo en busca de bugs, code smells y mejoras de calidad
when_to_use: Cuando el usuario pida revisar, auditar, o mejorar codigo existente
tags: [review, quality, refactor, bugs]
version: 1.0.0
author: OvandoCode
---

# Revision de codigo

## Checklist
1. Correccion: hay bugs evidentes, off-by-one, condiciones invertidas?
2. Manejo de errores: se capturan excepciones correctamente? se validan inputs?
3. Recursos: se cierran archivos, conexiones, subprocess?
4. Tipos: hay anotaciones? son correctas?
5. Duplicacion: se puede extraer funcion/clase?
6. Nombres: son descriptivos? verbos para funciones, sustantivos para clases?
7. Complejidad: funciones de mas de 50 lineas? anidamiento > 3 niveles?
8. Seguridad: inyeccion, path traversal, secrets hardcodeados?
9. Tests: el cambio tiene tests? cubren edge cases?
10. Performance: algoritmos O(n^2) evitables? queries N+1?

## Formato de salida
Agrupa por severidad:

### Criticos (rompen funcionalidad o seguridad)
- archivo:linea - descripcion + fix sugerido

### Importantes (deuda tecnica)
- ...

### Menores (estilo, preferencias)
- ...

## Reglas
- No cambies el codigo sin permiso; solo reporta.
- Si el usuario dice "aplica los fixes", hazlo uno por uno con edit_file.
- Cita archivo:linea exactos.
