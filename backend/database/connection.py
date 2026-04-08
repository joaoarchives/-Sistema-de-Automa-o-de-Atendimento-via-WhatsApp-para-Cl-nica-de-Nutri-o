import os
from contextlib import contextmanager
from threading import Lock
from time import monotonic, sleep

import mysql.connector
from mysql.connector import pooling
from mysql.connector.errors import PoolError

from config.settings import Config

_pool = None
_pool_pid = None
_pool_lock = Lock()
_SESSION_TIME_ZONE = "+00:00"


def _build_pool():
    return pooling.MySQLConnectionPool(
        pool_name=f"clinica_pool_{os.getpid()}",
        pool_size=Config.DB_POOL_SIZE,
        pool_reset_session=Config.DB_POOL_RESET_SESSION,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        connection_timeout=Config.DB_CONNECTION_TIMEOUT,
        autocommit=False,
    )


def _get_pool():
    global _pool, _pool_pid
    current_pid = os.getpid()
    with _pool_lock:
        if _pool is None or _pool_pid != current_pid:
            _pool = _build_pool()
            _pool_pid = current_pid
    return _pool


def _acquire_connection():
    pool = _get_pool()
    timeout = max(0.0, float(Config.DB_POOL_ACQUIRE_TIMEOUT))
    retry_interval = max(0.01, float(Config.DB_POOL_ACQUIRE_RETRY_INTERVAL))
    deadline = monotonic() + timeout

    while True:
        try:
            conn = pool.get_connection()
            _configure_connection_session(conn)
            return conn
        except PoolError:
            if timeout == 0 or monotonic() >= deadline:
                raise
            sleep(retry_interval)


def _configure_connection_session(conn) -> None:
    # The app persists UTC-naive datetimes in MySQL; every acquired session must
    # be pinned to UTC so reads/writes stay consistent regardless of host/db TZ.
    cursor = conn.cursor()
    try:
        cursor.execute("SET time_zone = %s", (_SESSION_TIME_ZONE,))
    finally:
        cursor.close()


@contextmanager
def get_db():
    """
    Uso:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            ...

    - Commit autom?tico ao sair sem erro.
    - Rollback autom?tico se ocorrer qualquer exce??o.
    - Conex?o devolvida ao pool em qualquer caso.
    """
    conn = _acquire_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_direct_db_connection():
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        connection_timeout=Config.DB_CONNECTION_TIMEOUT,
        autocommit=False,
    )
    _configure_connection_session(conn)
    return conn
