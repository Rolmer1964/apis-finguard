"""Testes da API. Não carregam o modelo de embedding real (stubado) nem o índice real (tmp dir)."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.rag_service import RagService
from tests.conftest import write_doc

client = TestClient(app)

PARA_A = "A politica interna determina que reclamacoes envolvendo o Banco Central recebam tratamento prioritario e prazo de quatro horas."
PARA_B = "Casos de fraude em cartao de credito devem ser encaminhados imediatamente a area de seguranca com abertura de chamado formal."


def _ingest_one_doc():
    write_doc("politica.txt", f"{PARA_A}\n\n{PARA_B}\n")
    return RagService(get_settings()).ingest()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_retrieve_indice_vazio():
    resp = client.post("/v1/rag/retrieve", json={"query": "qualquer coisa"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["chunks"] == []
    assert "índice vazio" in body["policy_context"]


def test_ingest_indexa_e_retrieve_encontra():
    stats = _ingest_one_doc()
    assert stats["chunks_added"] == 2
    assert stats["total_vectors_after"] == 2

    resp = client.post("/v1/rag/retrieve", json={"query": PARA_A})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["chunks"][0]["source"] == "politica.txt"
    assert body["chunks"][0]["score"] > 0.9  # query == trecho -> similaridade ~1
    assert "Trechos relevantes da Política Interna" in body["policy_context"]
    assert PARA_A in body["policy_context"]


def test_retrieve_respeita_k():
    _ingest_one_doc()
    resp = client.post("/v1/rag/retrieve", json={"query": PARA_B, "k": 1})
    assert resp.json()["count"] == 1


def test_stats_reflete_o_indice():
    _ingest_one_doc()
    resp = client.get("/v1/rag/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_vectors"] == 2
    assert len(body["files"]) == 1
    assert body["files"][0]["path"] == "politica.txt"
    assert body["files"][0]["chunks"] == 2
    assert body["updated_at"]


def test_ingest_incremental_pula_arquivo_inalterado():
    _ingest_one_doc()
    stats2 = RagService(get_settings()).ingest()
    assert stats2["skipped"] == ["politica.txt"]
    assert stats2["chunks_added"] == 0


def test_reset_apaga_indice():
    _ingest_one_doc()
    resp = client.post("/v1/rag/reset")
    assert resp.status_code == 200
    assert resp.json()["removed_index_files"] >= 1
    assert client.get("/v1/rag/stats").json()["total_vectors"] == 0


def test_ingest_endpoint_202_started(monkeypatch):
    monkeypatch.setattr(RagService, "run_ingest_bg", lambda self: None)
    resp = client.post("/v1/rag/ingest")
    assert resp.status_code == 202
    assert resp.json()["status"] == "started"


def test_ingest_endpoint_already_running(monkeypatch):
    monkeypatch.setattr(
        "app.routers.rag.get_ingest_state",
        lambda: {"status": "running", "stats": None, "error": None},
    )
    resp = client.post("/v1/rag/ingest")
    assert resp.status_code == 202
    assert resp.json()["status"] == "already_running"


def test_ingest_status_shape():
    resp = client.get("/v1/rag/ingest/status")
    assert resp.status_code == 200
    assert set(resp.json()) == {"status", "stats", "error"}


def test_retrieve_erro_embedding_502(monkeypatch):
    _ingest_one_doc()

    def boom(self, text):
        raise RuntimeError("modelo não carregado")

    monkeypatch.setattr(RagService, "_embed_one", boom)
    resp = client.post("/v1/rag/retrieve", json={"query": "algo"})
    assert resp.status_code == 502
    assert resp.json()["detail"]["codigo"] == "EMBED_MODEL_ERRO"


def test_startup_probe_aborta_sem_modelo(monkeypatch):
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(PROBE_ON_STARTUP=True, INGEST_ON_STARTUP=False))

    def boom(self):
        raise OSError("modelo de embedding não encontrado")

    monkeypatch.setattr(RagService, "ping", boom)
    with pytest.raises(RuntimeError, match="EMBED_MODEL_ERRO"):
        with TestClient(app):
            pass
