"""Fixtures dos testes.

O serviço grava artefatos em disco. Os testes apontam `OUTPUT_DIR` para um
diretório temporário (definido antes de importar `app.config`, que cacheia as
settings) e limpam esse diretório antes de cada teste.
"""

import os
import tempfile
from pathlib import Path

_TMP_OUTPUT = Path(tempfile.gettempdir()) / "fin_report_writer_tests_output"
os.environ["OUTPUT_DIR"] = str(_TMP_OUTPUT)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean_output_dir():
    if _TMP_OUTPUT.exists():
        for f in _TMP_OUTPUT.iterdir():
            if f.is_file():
                f.unlink()
    _TMP_OUTPUT.mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def output_dir() -> Path:
    return _TMP_OUTPUT
