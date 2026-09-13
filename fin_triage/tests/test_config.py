"""Testes da resolução de ANTHROPIC_API_KEY via SSM Parameter Store.

A busca acontece uma única vez, dentro de Settings.model_post_init — aqui
testamos isso diretamente (sem passar pelo get_settings() cacheado) para
cobrir os dois caminhos: busca no SSM quando a chave falta, e nenhuma
chamada quando ela já veio definida.
"""

from app.config import Settings


class _FakeSSMClient:
    def __init__(self, value: str):
        self._value = value
        self.calls: list[str] = []

    def get_parameter(self, Name, WithDecryption):
        self.calls.append(Name)
        assert WithDecryption is True
        return {"Parameter": {"Value": self._value}}


def _fake_boto3_session(fake_client):
    class _Session:
        def __init__(self, **kwargs):
            pass

        def client(self, service_name, **kwargs):
            assert service_name == "ssm"
            return fake_client

    return _Session


def test_busca_no_ssm_quando_chave_ausente(monkeypatch):
    fake_client = _FakeSSMClient("chave-vinda-do-ssm")
    monkeypatch.setattr("app.config.boto3.Session", _fake_boto3_session(fake_client))

    s = Settings(ANTHROPIC_API_KEY_SSM_PARAM="/apis-finguard/prod/ANTHROPIC_API_KEY")

    assert s.ANTHROPIC_API_KEY == "chave-vinda-do-ssm"
    assert fake_client.calls == ["/apis-finguard/prod/ANTHROPIC_API_KEY"]


def test_nao_busca_no_ssm_quando_chave_ja_definida(monkeypatch):
    fake_client = _FakeSSMClient("nao-deveria-ser-usada")
    monkeypatch.setattr("app.config.boto3.Session", _fake_boto3_session(fake_client))

    s = Settings(
        ANTHROPIC_API_KEY="chave-do-env",
        ANTHROPIC_API_KEY_SSM_PARAM="/apis-finguard/prod/ANTHROPIC_API_KEY",
    )

    assert s.ANTHROPIC_API_KEY == "chave-do-env"
    assert fake_client.calls == []


def test_nao_busca_no_ssm_quando_param_nao_configurado(monkeypatch):
    def _boom(**kwargs):
        raise AssertionError("boto3.Session não deveria ser chamado sem ANTHROPIC_API_KEY_SSM_PARAM")
    monkeypatch.setattr("app.config.boto3.Session", _boom)

    s = Settings()

    assert s.ANTHROPIC_API_KEY is None


def test_erro_no_ssm_vira_runtime_error_claro(monkeypatch):
    class _BoomClient:
        def get_parameter(self, Name, WithDecryption):
            raise Exception("AccessDenied")

    monkeypatch.setattr("app.config.boto3.Session", _fake_boto3_session(_BoomClient()))

    try:
        Settings(ANTHROPIC_API_KEY_SSM_PARAM="/apis-finguard/prod/ANTHROPIC_API_KEY")
        assert False, "deveria ter levantado RuntimeError"
    except RuntimeError as exc:
        assert "SSM_ERRO" in str(exc)
        assert "/apis-finguard/prod/ANTHROPIC_API_KEY" in str(exc)
