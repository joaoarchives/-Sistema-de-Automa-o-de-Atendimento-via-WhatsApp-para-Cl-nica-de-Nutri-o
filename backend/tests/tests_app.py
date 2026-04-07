from unittest.mock import Mock

import pytest

import app as app_module
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


def test_webhook_ignora_mensagem_duplicada(client, monkeypatch):
    chamadas_dedup = [True, False]
    processar_mensagem = Mock(return_value=BotResponse(texto="Olá"))
    send_whatsapp = Mock(return_value={"response": {"messages": [{"id": "wamid.1"}]}, "payload": {"type": "text"}})

    monkeypatch.setattr(app_module, "register_processed_webhook_message", lambda message_id: chamadas_dedup.pop(0))
    monkeypatch.setattr(app_module, "salvar_log_whatsapp", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_module, "processar_mensagem", processar_mensagem)
    monkeypatch.setattr(app_module, "send_whatsapp_message", send_whatsapp)

    resposta_1 = client.post("/webhook", json=webhook_payload("wamid.123"))
    resposta_2 = client.post("/webhook", json=webhook_payload("wamid.123"))

    assert resposta_1.status_code == 200
    assert resposta_2.status_code == 200
    processar_mensagem.assert_called_once_with("5538999999999", "oi")
    send_whatsapp.assert_called_once()
