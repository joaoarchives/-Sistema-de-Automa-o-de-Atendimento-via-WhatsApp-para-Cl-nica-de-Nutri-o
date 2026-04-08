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
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def auth_headers():
    token = jwt.encode(
        {"usuario": "drpaulo", "exp": datetime.now(UTC) + timedelta(hours=1)},
        api_module.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class FakePaymentState:
    def __init__(self, row):
        self.row = row


class FakePaymentCursor:
    def __init__(self, state):
        self.state = state

    def execute(self, query, params=None):
        normalized = " ".join(query.split())

        if "SELECT" in normalized and "FROM consultas c" in normalized and "FOR UPDATE" in normalized:
            return None

        if normalized.startswith("UPDATE consultas SET status = 'confirmado'"):
            self.state.row["status"] = "confirmado"
            self.state.row["pagamento_confirmado_em"] = self.state.row.get("pagamento_confirmado_em") or params[0]
            self.state.row["pagamento_notificacao_em_andamento"] = 1
            self.state.row["pagamento_notificacao_lock_em"] = params[1]
            self.state.row["motivo_cancelamento"] = None
            return None

        if normalized.startswith("UPDATE consultas SET confirmacao_whatsapp_enviada_em = COALESCE"):
            if params[0] is not None and not self.state.row.get("confirmacao_whatsapp_enviada_em"):
                self.state.row["confirmacao_whatsapp_enviada_em"] = params[0]
            return None

        if normalized.startswith("UPDATE consultas SET recomendacoes_whatsapp_enviadas_em = COALESCE"):
            if params[0] is not None and not self.state.row.get("recomendacoes_whatsapp_enviadas_em"):
                self.state.row["recomendacoes_whatsapp_enviadas_em"] = params[0]
            return None

        if normalized.startswith("UPDATE consultas SET pagamento_notificacao_em_andamento = 0"):
            self.state.row["pagamento_notificacao_em_andamento"] = 0
            self.state.row["pagamento_notificacao_lock_em"] = None
            return None

        if normalized.startswith("UPDATE consultas SET confirmacao_whatsapp_enviada_em = COALESCE(confirmacao_whatsapp_enviada_em, %s), pagamento_notificacao_em_andamento = 0"):
            if params[0] is not None and not self.state.row.get("confirmacao_whatsapp_enviada_em"):
                self.state.row["confirmacao_whatsapp_enviada_em"] = params[0]
            self.state.row["pagamento_notificacao_em_andamento"] = 0
            self.state.row["pagamento_notificacao_lock_em"] = None
            return None

        if normalized.startswith("UPDATE consultas SET recomendacoes_whatsapp_enviadas_em = COALESCE(recomendacoes_whatsapp_enviadas_em, %s), pagamento_notificacao_em_andamento = 0"):
            if params[0] is not None and not self.state.row.get("recomendacoes_whatsapp_enviadas_em"):
                self.state.row["recomendacoes_whatsapp_enviadas_em"] = params[0]
            self.state.row["pagamento_notificacao_em_andamento"] = 0
            self.state.row["pagamento_notificacao_lock_em"] = None
            return None

        raise AssertionError(f"SQL nao esperado: {normalized}")

    def fetchone(self):
        return dict(self.state.row)


class FakePaymentConn:
    def __init__(self, state):
        self.state = state

    def cursor(self, dictionary=False):
        return FakePaymentCursor(self.state)


@contextmanager
def fake_payment_db(state):
    yield FakePaymentConn(state)


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


def test_auth_configurada_exige_secret_key_forte(monkeypatch):
    monkeypatch.setattr(api_module, "SECRET_KEY", "curta")
    monkeypatch.setattr(api_module, "MEDICO_USER", "drpaulo")
    monkeypatch.setattr(api_module, "MEDICO_PASS_HASH", "hash")

    assert api_module.auth_configurada() is False


def test_auth_configurada_exige_medico_pass_hash(monkeypatch):
    monkeypatch.setattr(api_module, "SECRET_KEY", "segredo-de-teste-com-32-bytes-ok")
    monkeypatch.setattr(api_module, "MEDICO_USER", "drpaulo")
    monkeypatch.setattr(api_module, "MEDICO_PASS_HASH", "")

    assert api_module.auth_configurada() is False


def test_login_falha_fechado_sem_medico_pass_hash(client, monkeypatch):
    monkeypatch.setattr(api_module, "MEDICO_PASS_HASH", "")

    resposta = client.post("/api/auth/login", json={"usuario": "drpaulo", "senha": "senha123"})

    assert resposta.status_code == 503
    assert "MEDICO_PASS_HASH" in resposta.get_json()["erro"]


def test_historico_rejeita_pagina_invalida(client):
    resposta = client.get("/api/consultas/historico?pagina=abc", headers=auth_headers())

    assert resposta.status_code == 400
    assert "pagina" in resposta.get_json()["erro"]


def test_historico_rejeita_por_pagina_acima_do_limite(client):
    resposta = client.get("/api/consultas/historico?por_pagina=9999", headers=auth_headers())

    assert resposta.status_code == 400
    assert "por_pagina" in resposta.get_json()["erro"]


def test_confirmar_pagamento_retorna_aviso_quando_notificacao_falha(client, monkeypatch):
    state = FakePaymentState({
        "id": 1,
        "status": "aguardando_pagamento",
        "data": date(2026, 4, 10),
        "horario": "09:00:00",
        "telefone": "5538999999999",
        "pagamento_confirmado_em": None,
        "pagamento_notificacao_em_andamento": 0,
        "pagamento_notificacao_lock_em": None,
        "confirmacao_whatsapp_enviada_em": None,
        "recomendacoes_whatsapp_enviadas_em": None,
        "confirmacao_logada": 0,
        "recomendacoes_logadas": 0,
    })

    monkeypatch.setattr("database.connection.get_db", lambda: fake_payment_db(state))
    monkeypatch.setattr("services.whatsapp.send_whatsapp_message", lambda telefone, texto: {"response": {"messages": [{"id": "wamid.1"}]}, "payload": {"type": "text"}})
    monkeypatch.setattr("services.whatsapp.send_recomendacoes_pre_consulta", lambda telefone: {"response": {}, "payload": {"type": "text"}})
    monkeypatch.setattr(api_module, "registrar_envio_whatsapp", lambda *args, **kwargs: None)
    monkeypatch.setattr("database.estados.get_estado", lambda telefone: ("pagamento_em_analise", {}))
    monkeypatch.setattr("database.estados.set_estado", lambda telefone, estado, dados: None)

    resposta = client.patch("/api/consultas/1/confirmar-pagamento", headers=auth_headers())

    body = resposta.get_json()
    assert resposta.status_code == 200
    assert body["status"] == "confirmado"
    assert body["idempotente"] is False
    assert body["notificacao_enviada"] is False
    assert "recomendacoes" in body["aviso"].lower()
    assert state.row["confirmacao_whatsapp_enviada_em"] is not None
    assert state.row["recomendacoes_whatsapp_enviadas_em"] is None


def test_confirmar_pagamento_e_idempotente_quando_ja_notificado(client, monkeypatch):
    now_db = datetime.now(UTC).replace(tzinfo=None)
    state = FakePaymentState({
        "id": 1,
        "status": "confirmado",
        "data": date(2026, 4, 10),
        "horario": "09:00:00",
        "telefone": "5538999999999",
        "pagamento_confirmado_em": now_db,
        "pagamento_notificacao_em_andamento": 0,
        "pagamento_notificacao_lock_em": None,
        "confirmacao_whatsapp_enviada_em": now_db,
        "recomendacoes_whatsapp_enviadas_em": now_db,
        "confirmacao_logada": 1,
        "recomendacoes_logadas": 1,
    })

    monkeypatch.setattr("database.connection.get_db", lambda: fake_payment_db(state))
    monkeypatch.setattr("services.whatsapp.send_whatsapp_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Nao deveria enviar novamente")))
    monkeypatch.setattr("services.whatsapp.send_recomendacoes_pre_consulta", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Nao deveria reenviar recomendacoes")))

    resposta = client.patch("/api/consultas/1/confirmar-pagamento", headers=auth_headers())

    body = resposta.get_json()
    assert resposta.status_code == 200
    assert body["idempotente"] is True
    assert body["notificacao_enviada"] is True


def test_confirmar_pagamento_nao_duplica_envio_com_lock_ativo(client, monkeypatch):
    now_db = datetime.now(UTC).replace(tzinfo=None)
    state = FakePaymentState({
        "id": 1,
        "status": "confirmado",
        "data": date(2026, 4, 10),
        "horario": "09:00:00",
        "telefone": "5538999999999",
        "pagamento_confirmado_em": now_db,
        "pagamento_notificacao_em_andamento": 1,
        "pagamento_notificacao_lock_em": now_db,
        "confirmacao_whatsapp_enviada_em": now_db,
        "recomendacoes_whatsapp_enviadas_em": None,
        "confirmacao_logada": 1,
        "recomendacoes_logadas": 0,
    })

    monkeypatch.setattr("database.connection.get_db", lambda: fake_payment_db(state))
    monkeypatch.setattr("services.whatsapp.send_whatsapp_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Nao deveria enviar com lock ativo")))
    monkeypatch.setattr("services.whatsapp.send_recomendacoes_pre_consulta", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Nao deveria enviar com lock ativo")))

    resposta = client.patch("/api/consultas/1/confirmar-pagamento", headers=auth_headers())

    body = resposta.get_json()
    assert resposta.status_code == 200
    assert body["idempotente"] is True
    assert "processada" in body["aviso"].lower()


def test_confirmar_pagamento_atualiza_estado_mesmo_quando_notificacao_falha(client, monkeypatch):
    state = FakePaymentState({
        "id": 1,
        "status": "aguardando_pagamento",
        "data": date(2026, 4, 10),
        "horario": "09:00:00",
        "telefone": "5538999999999",
        "pagamento_confirmado_em": None,
        "pagamento_notificacao_em_andamento": 0,
        "pagamento_notificacao_lock_em": None,
        "confirmacao_whatsapp_enviada_em": None,
        "recomendacoes_whatsapp_enviadas_em": None,
        "confirmacao_logada": 0,
        "recomendacoes_logadas": 0,
    })
    chamadas_set_estado = []

    monkeypatch.setattr("database.connection.get_db", lambda: fake_payment_db(state))
    monkeypatch.setattr(
        "services.whatsapp.send_whatsapp_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("falha no envio")),
    )
    monkeypatch.setattr("services.whatsapp.send_recomendacoes_pre_consulta", lambda telefone: {"response": {}, "payload": {"type": "text"}})
    monkeypatch.setattr(api_module, "registrar_envio_whatsapp", lambda *args, **kwargs: None)
    monkeypatch.setattr("database.estados.get_estado", lambda telefone: ("pagamento_em_analise", {}))
    monkeypatch.setattr(
        "database.estados.set_estado",
        lambda telefone, estado, dados: chamadas_set_estado.append((telefone, estado, dados)),
    )

    resposta = client.patch("/api/consultas/1/confirmar-pagamento", headers=auth_headers())

    body = resposta.get_json()
    assert resposta.status_code == 200
    assert body["status"] == "confirmado"
    assert body["notificacao_enviada"] is False
    assert body["estado_atualizado"] is True
    assert chamadas_set_estado
    assert chamadas_set_estado[0][1] == "consulta_confirmada"
