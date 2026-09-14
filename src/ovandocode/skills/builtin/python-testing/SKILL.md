---
name: python-testing
description: Escribir y ejecutar tests de Python con pytest siguiendo buenas practicas
when_to_use: Cuando el usuario pida escribir tests, corregir tests fallidos, o cuando modifiques codigo que tenga tests asociados
tags: [python, testing, pytest, tdd]
version: 1.0.0
author: OvandoCode
---

# Escribir tests de Python con pytest

## Estructura
- Los tests van en `tests/` paralelo a `src/`.
- Un archivo `test_<modulo>.py` por modulo testeado.
- Nombra cada test `test_<comportamiento>_<condicion>`.

## Reglas
1. Un assert por test cuando sea posible.
2. Usa fixtures en vez de setup/teardown manuales.
3. Parametriza casos similares con pytest.mark.parametrize.
4. Async tests requieren pytest-asyncio y asyncio_mode = auto.
5. Cubre: happy path, edge cases, errores esperados, y al menos un caso limite.

## Plantilla basica

    import pytest
    from mi_modulo import mi_funcion

    @pytest.mark.parametrize("entrada,esperado", [(1,2),(2,4),(0,0),(-1,-2)])
    def test_mi_funcion_duplica(entrada, esperado):
        assert mi_funcion(entrada) == esperado

    def test_mi_funcion_falla_con_string():
        with pytest.raises(TypeError):
            mi_funcion("no soy numero")

## Comandos utiles
- Correr todo: uv run pytest
- Un archivo: uv run pytest tests/test_foo.py -v
- Con cobertura: uv run pytest --cov=src/ovandocode --cov-report=term-missing
- Detener en el primer fallo: uv run pytest -x

## Flujo
1. grep para encontrar tests existentes del modulo.
2. read_file del modulo y sus tests actuales.
3. Escribe/edita el test con edit_file (o write_file si es nuevo).
4. Corre uv run pytest <ruta> con run_powershell.
5. Si falla, itera. No declares "listo" sin ver exit=0.
