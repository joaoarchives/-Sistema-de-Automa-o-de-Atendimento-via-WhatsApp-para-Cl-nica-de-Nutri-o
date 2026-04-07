from contextlib import contextmanager

import database.consultas as consultas_module


class FakeCursor:
    def __init__(self, fetch_rows=None, rowcount=1):
        self.fetch_rows = list(fetch_rows or [])
        self.rowcount = rowcount
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self):
        if self.fetch_rows:
            return self.fetch_rows.pop(0)
        return None


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor


@contextmanager
def fake_db(cursor):
    yield FakeConn(cursor)


def test_atualizar_status_consulta_persiste_motivo_cancelamento(monkeypatch):
    cursor = FakeCursor(rowcount=1)
    monkeypatch.setattr(consultas_module, "get_db", lambda: fake_db(cursor))

    sucesso = consultas_module.atualizar_status_consulta(12, "cancelado", motivo="Paciente pediu cancelamento")

    assert sucesso is True
    sql, params = cursor.executed[-1]
    assert "motivo_cancelamento = %s" in sql
    assert params == ("cancelado", "Paciente pediu cancelamento", 12)


def test_cancelar_ultima_consulta_define_motivo_padrao(monkeypatch):
    cursor = FakeCursor(fetch_rows=[{"id": 7}], rowcount=1)
    monkeypatch.setattr(consultas_module, "get_db", lambda: fake_db(cursor))

    sucesso = consultas_module.cancelar_ultima_consulta("5538999999999")

    assert sucesso is True
    _, params = cursor.executed[-1]
    assert params[0] == "Cancelado pelo paciente via WhatsApp"
    assert params[1] == 7
