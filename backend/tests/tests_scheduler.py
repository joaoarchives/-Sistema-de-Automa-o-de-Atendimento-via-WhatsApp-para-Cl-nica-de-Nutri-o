from contextlib import contextmanager
from datetime import UTC, datetime

import services.scheduler as scheduler_module


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self):
        return [{"id": 5, "pagamento_expira_em": datetime.now(UTC).replace(tzinfo=None), "telefone": "5538999999999"}]


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor


@contextmanager
def fake_db(cursor):
    yield FakeConn(cursor)


def test_expirar_pagamentos_pendentes_persiste_motivo(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(scheduler_module, "get_db", lambda: fake_db(cursor))
    monkeypatch.setattr(scheduler_module, "send_whatsapp_message", lambda *args, **kwargs: None)

    scheduler_module.expirar_pagamentos_pendentes()

    update_sql, params = cursor.executed[-1]
    assert "motivo_cancelamento = %s" in update_sql
    assert params[0] == "Cancelado automaticamente por expiracao do pagamento"
    assert params[1] == 5
