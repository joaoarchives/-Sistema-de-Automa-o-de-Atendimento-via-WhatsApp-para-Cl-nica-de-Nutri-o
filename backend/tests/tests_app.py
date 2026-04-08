import hashlib
import hmac
import json
from unittest.mock import Mock

import pytest

import app as app_module
import api as api_module
from services.bot_response import BotResponse


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def webhook_payload(message_id: str):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": "5538999999999",
                                    "type": "text",
                                    "text": {"body": "oi"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def assinatura_header(payload_bytes: bytes, secret: str) -> dict:
    assinatura = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={assinatura}"}


def test_webhook_rejeita_assinatura_invalida(client, monkeypatch):
    monkeypatch.setattr(app_module, "WEBHOOK_APP_SECRET", "segredo-webhook")

    payload = json.dumps(webhook_payload("wamid.123")).encode("utf-8")
    resposta = client.post(
        "/webhook",
        data=payload,
        content_type="application/json",
        headers={"X-Hub-Signature-256": "sha256=assinatura-invalida"},
    )

    assert resposta.status_code == 403


def test_webhook_falha_fechado_sem_secret(client, monkeypatch):
    monkeypatch.setattr(app_module, "WEBHOOK_APP_SECRET", "")

    payload = json.dumps(webhook_payload("wamid.123")).encode("utf-8")
    resposta = client.post(
        "/webhook",
        data=payload,
        content_type="application/json",
    )

    assert resposta.status_code == 503


def test_webhook_ignora_mensagem_duplicada(client, monkeypatch):
    monkeypatch.setattr(app_module, "WEBHOOK_APP_SECRET", "segredo-webhook")

    chamadas_dedup = [True, False]
    processar_mensagem = Mock(return_value=BotResponse(texto="Olá"))
    send_whatsapp = Mock(return_value={"response": {"messages": [{"id": "wamid.1"}]}, "payload": {"type": "text"}})

    monkeypatch.setattr(app_module, "register_processed_webhook_message", lambda message_id: chamadas_dedup.pop(0))
    monkeypatch.setattr(app_module, "salvar_log_whatsapp", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_module, "processar_mensagem", processar_mensagem)
    monkeypatch.setattr(app_module, "send_whatsapp_message", send_whatsapp)

    payload_1 = json.dumps(webhook_payload("wamid.123")).encode("utf-8")
    headers_1 = assinatura_header(payload_1, app_module.WEBHOOK_APP_SECRET)
    resposta_1 = client.post("/webhook", data=payload_1, content_type="application/json", headers=headers_1)

    payload_2 = json.dumps(webhook_payload("wamid.123")).encode("utf-8")
    headers_2 = assinatura_header(payload_2, app_module.WEBHOOK_APP_SECRET)
    resposta_2 = client.post("/webhook", data=payload_2, content_type="application/json", headers=headers_2)

    assert resposta_1.status_code == 200
    assert resposta_2.status_code == 200
    processar_mensagem.assert_called_once_with("5538999999999", "oi")
    send_whatsapp.assert_called_once()


def test_api_bootstrap_schema_antes_das_rotas(client, monkeypatch):
    app_module.app.config["TESTING"] = False
    chamadas = []

    monkeypatch.setattr(app_module, "ensure_database_ready", lambda: chamadas.append("ok"))
    monkeypatch.setattr(api_module, "auth_configurada", lambda: True)

    resposta = client.get("/api/consultas/historico")

    assert resposta.status_code == 401
    assert chamadas == ["ok"]


def test_api_retorna_503_quando_bootstrap_schema_falha(client, monkeypatch):
    app_module.app.config["TESTING"] = False

    def quebrar_bootstrap():
        raise RuntimeError("db indisponivel")

    monkeypatch.setattr(app_module, "ensure_database_ready", quebrar_bootstrap)

    resposta = client.get("/api/consultas/historico")

    assert resposta.status_code == 503
    assert "banco" in resposta.get_json()["erro"].lower()
