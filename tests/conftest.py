"""Fixtures compartidas de pytest."""
import os
import sys
from pathlib import Path

import pytest

# Asegurar que src/ esta en el path
ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Directorio de proyecto temporal."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "archivo.txt").write_text("linea1\nlinea2\nlinea3\n", encoding="utf-8")
    (tmp_path / "subdir" / "modulo.py").write_text(
        "def hola():\n    return 'hola'\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch):
    """Limpia variables OVANDOCODE_* del entorno."""
    for k in list(os.environ):
        if k.startswith("OVANDOCODE_"):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch
