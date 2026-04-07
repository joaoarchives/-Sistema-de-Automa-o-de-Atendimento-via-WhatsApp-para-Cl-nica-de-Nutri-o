from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest
from werkzeug.security import generate_password_hash

import api as api_module
from app import app as flask_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api_module, "SECRET_KEY", "segredo-de-teste-com-32-bytes-ok")
    monkeypatch.setattr(api_module, "MEDICO_USER", "drpaulo")
    monkeypatch.setattr(api_module, "MEDICO_PASS_HASH", generate_password_hash("senha123"))
    monkeypatch.setattr(api_module, "_LEGACY_PASSWORD_HASH", "")
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def auth_headers():
    token = jwt.encode(
        {"usuario": "drpaulo", "exp": datetime.now(UTC) + timedelta(hours=1)},
        api_module.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_login_bloqueado_retorna_429(client, monkeypatch):
    monkeypatch.setattr(
        api_module,
        "get_login_rate_limit",
        lambda identificador: {
            "tentativas": 5,
            "bloqueado": True,
            "bloqueado_ate": datetime.now(UTC) + timedelta(minutes=10),
        },
    )

    resposta = client.post("/api/auth/login", json={"usuario": "drpaulo", "senha": "senha123"})

    assert resposta.status_code == 429
    assert "Muitas tentativas" in resposta.get_json()["erro"]


def test_login_invalido_registra_tentativa(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        api_module,
        "get_login_rate_limit",
        lambda identificador: {"tentativas": 0, "bloqueado": False, "bloqueado_ate": None},
    )

    def fake_register(identificador, **kwargs):
        chamadas.append((identificador, kwargs))
        return {"tentativas": 1, "bloqueado": False, "bloqueado_ate": None}

    monkeypatch.setattr(api_module, "register_login_failure", fake_register)

    resposta = client.post("/api/auth/login", json={"usuario": "drpaulo", "senha": "errada"})

    assert resposta.status_code == 401
    assert chamadas


def test_historico_rejeita_pagina_invalida(client):
    resposta = client.get("/api/consultas/historico?pagina=abc", headers=auth_headers())

    assert resposta.status_code == 400
    assert "pagina" in resposta.get_json()["erro"]


def test_historico_rejeita_por_pagina_acima_do_limite(client):
    resposta = client.get("/api/consultas/historico?por_pagina=9999", headers=auth_headers())

    assert resposta.status_code == 400
    assert "por_pagina" in resposta.get_json()["erro"]


def test_confirmar_pagamento_retorna_aviso_quando_notificacao_falha(client, monkeypatch):
    monkeypatch.setattr(api_module, "atualizar_status_consulta", lambda consulta_id, status: True)

    class FakeCursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return {"telefone": "5538999999999", "data": date(2026, 4, 10), "horario": "09:00:00"}

    class FakeConn:
        def cursor(self, dictionary=False):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    @contextmanager
    def fake_get_db():
        yield FakeConn()

    monkeypatch.setattr("database.connection.get_db", fake_get_db)
    monkeypatch.setattr("services.whatsapp.send_whatsapp_message", lambda telefone, texto: {"response": {"messages": [{"id": "wamid.1"}]}, "payload": {"type": "text"}})
    monkeypatch.setattr("services.whatsapp.send_recomendacoes_pre_consulta", lambda telefone: {"response": {}, "payload": {"type": "text"}})
    monkeypatch.setattr(api_module, "registrar_envio_whatsapp", lambda *args, **kwargs: None)
    monkeypatch.setattr("database.estados.get_estado", lambda telefone: ("pagamento_em_analise", {}))
    monkeypatch.setattr("database.estados.set_estado", lambda telefone, estado, dados: None)

    resposta = client.patch("/api/consultas/1/confirmar-pagamento", headers=auth_headers())

    body = resposta.get_json()
    assert resposta.status_code == 200
    assert body["status"] == "confirmado"
    assert body["notificacao_enviada"] is False
    assert "recomendações" in body["aviso"].lower()
