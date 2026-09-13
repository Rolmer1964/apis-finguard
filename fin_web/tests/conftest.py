"""Fixtures dos testes do fin_web.

Nenhuma folha nem o orquestrador sobem: o `httpx` do fin_web é interceptado
com `respx`. O `ORCHESTRATOR_URL` aponta para um host fake e estável.
"""

import os

import pytest

os.environ.setdefault("ORCHESTRATOR_URL", "http://orch.test")
os.environ.setdefault("API_KEY", "")

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

ORCH = "http://orch.test"


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    # Isola o arquivo de recorde da cobrinha em tmp.
    snake = tmp_path / "snake_record.json"
    os.environ["SNAKE_RECORD_PATH"] = str(snake)
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
