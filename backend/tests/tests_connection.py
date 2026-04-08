import database.connection as connection_module


class FakeCursor:
    def __init__(self, statements):
        self._statements = statements

    def execute(self, query, params=None):
        self._statements.append((" ".join(query.split()), params))

    def close(self):
        return None


class FakeConn:
    def __init__(self):
        self.statements = []

    def cursor(self, dictionary=False):
        return FakeCursor(self.statements)


def test_acquire_connection_configura_sessao_utc(monkeypatch):
    fake_conn = FakeConn()

    class FakePool:
        def get_connection(self):
            return fake_conn

    monkeypatch.setattr(connection_module, "_get_pool", lambda: FakePool())
    monkeypatch.setattr(connection_module.Config, "DB_POOL_ACQUIRE_TIMEOUT", 0)

    conn = connection_module._acquire_connection()

    assert conn is fake_conn
    assert fake_conn.statements == [("SET time_zone = %s", ("+00:00",))]


def test_get_direct_db_connection_configura_sessao_utc(monkeypatch):
    fake_conn = FakeConn()
    called = {}

    def fake_connect(**kwargs):
        called.update(kwargs)
        return fake_conn

    monkeypatch.setattr(connection_module.mysql.connector, "connect", fake_connect)

    conn = connection_module.get_direct_db_connection()

    assert conn is fake_conn
    assert called["autocommit"] is False
    assert fake_conn.statements == [("SET time_zone = %s", ("+00:00",))]
