from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import services.scheduler as scheduler_module


class FakeCursor:
    def __init__(self, rows=None):
        self.executed = []
        self._rows = rows or []

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor


@contextmanager
def fake_db(cursor):
    yield FakeConn(cursor)


def test_expirar_pagamentos_pendentes_persiste_motivo(monkeypatch):
    cursor = FakeCursor([
        {"id": 5, "pagamento_expira_em": datetime.now(UTC).replace(tzinfo=None), "telefone": "5538999999999"}
    ])
    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda *args, **kwargs: None)

    scheduler_module.expirar_pagamentos_pendentes()

    update_sql, params = cursor.executed[-1]
    assert "motivo_cancelamento = %s" in update_sql
    assert params[0] == "Cancelado automaticamente por expiracao do pagamento"
    assert params[1] == 5


def test_verificar_lembretes_envia_24h(monkeypatch):
    agora = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    cursor = FakeCursor([
        {
            "id": 11,
            "data": datetime(2026, 4, 9).date(),
            "horario": timedelta(hours=12),
            "telefone": "5538999999999",
            "lembrete_24h_enviado": 0,
            "lembrete_12h_enviado": 0,
        }
    ])
    envios = []

    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "utc_now", lambda: agora)
    monkeypatch.setattr(scheduler_module, "local_schedule_to_utc", lambda data, horario: agora + timedelta(hours=24))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda telefone, mensagem: envios.append((telefone, mensagem)))

    scheduler_module.verificar_lembretes()

    assert len(envios) == 1
    assert "Faltam 24h" in envios[0][1]
    assert any("SET lembrete_24h_enviado = 1" in sql for sql, _ in cursor.executed)
    assert not any("SET lembrete_12h_enviado = 1" in sql for sql, _ in cursor.executed)


def test_verificar_lembretes_envia_12h(monkeypatch):
    agora = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    cursor = FakeCursor([
        {
            "id": 12,
            "data": datetime(2026, 4, 8).date(),
            "horario": timedelta(hours=23, minutes=59),
            "telefone": "5538999999998",
            "lembrete_24h_enviado": 1,
            "lembrete_12h_enviado": 0,
        }
    ])
    envios = []

    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "utc_now", lambda: agora)
    monkeypatch.setattr(scheduler_module, "local_schedule_to_utc", lambda data, horario: agora + timedelta(hours=12))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda telefone, mensagem: envios.append((telefone, mensagem)))

    scheduler_module.verificar_lembretes()

    assert len(envios) == 1
    assert "Faltam 12h" in envios[0][1]
    assert any("SET lembrete_12h_enviado = 1" in sql for sql, _ in cursor.executed)


def test_verificar_lembretes_nao_envia_fora_da_janela(monkeypatch):
    agora = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    cursor = FakeCursor([
        {
            "id": 13,
            "data": datetime(2026, 4, 9).date(),
            "horario": timedelta(hours=12, minutes=10),
            "telefone": "5538999999997",
            "lembrete_24h_enviado": 0,
            "lembrete_12h_enviado": 0,
        }
    ])
    envios = []

    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "utc_now", lambda: agora)
    monkeypatch.setattr(scheduler_module, "local_schedule_to_utc", lambda data, horario: agora + timedelta(hours=24, minutes=10))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda telefone, mensagem: envios.append((telefone, mensagem)))

    scheduler_module.verificar_lembretes()

    assert envios == []
    assert not any("lembrete_24h_enviado = 1" in sql or "lembrete_12h_enviado = 1" in sql for sql, _ in cursor.executed)


def test_verificar_lembretes_nao_reenvia_flag_ja_marcada(monkeypatch):
    agora = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    cursor = FakeCursor([
        {
            "id": 14,
            "data": datetime(2026, 4, 9).date(),
            "horario": timedelta(hours=12),
            "telefone": "5538999999996",
            "lembrete_24h_enviado": 1,
            "lembrete_12h_enviado": 1,
        }
    ])
    envios = []

    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "utc_now", lambda: agora)
    monkeypatch.setattr(scheduler_module, "local_schedule_to_utc", lambda data, horario: agora + timedelta(hours=24))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda telefone, mensagem: envios.append((telefone, mensagem)))

    scheduler_module.verificar_lembretes()

    assert envios == []


def test_verificar_lembretes_nao_envia_consulta_passada(monkeypatch):
    agora = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    cursor = FakeCursor([
        {
            "id": 15,
            "data": datetime(2026, 4, 8).date(),
            "horario": timedelta(hours=8),
            "telefone": "5538999999995",
            "lembrete_24h_enviado": 0,
            "lembrete_12h_enviado": 0,
        }
    ])
    envios = []

    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "utc_now", lambda: agora)
    monkeypatch.setattr(scheduler_module, "local_schedule_to_utc", lambda data, horario: agora - timedelta(minutes=1))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda telefone, mensagem: envios.append((telefone, mensagem)))

    scheduler_module.verificar_lembretes()

    assert envios == []


def test_descrever_jobs_scheduler_retorna_jobs_esperados():
    jobs = scheduler_module.descrever_jobs_scheduler()

    assert [job["id"] for job in jobs] == [
        "expirar_pagamentos",
        "verificar_lembretes",
        "enviar_resumo_do_dia",
    ]
    assert jobs[0]["trigger"] == "interval"
    assert jobs[1]["kwargs"]["minutes"] == 1
    assert jobs[2]["trigger"] == "cron"
