import pytest

import services.whatsapp as whatsapp


def test_post_whatsapp_falha_sem_config_em_producao(monkeypatch):
    monkeypatch.setattr(whatsapp, "WHATSAPP_TOKEN", "")
    monkeypatch.setattr(whatsapp, "WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.delenv("WHATSAPP_ALLOW_MOCK", raising=False)

    with pytest.raises(RuntimeError, match="não configurados corretamente"):
        whatsapp._post_whatsapp({"type": "text"}, "Erro ao enviar mensagem")


def test_post_whatsapp_permita_mock_somente_quando_explicito(monkeypatch):
    monkeypatch.setattr(whatsapp, "WHATSAPP_TOKEN", "")
    monkeypatch.setattr(whatsapp, "WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.setenv("WHATSAPP_ALLOW_MOCK", "true")

    resultado = whatsapp._post_whatsapp({"type": "text"}, "Erro ao enviar mensagem")

    assert resultado["response"]["mocked"] is True
