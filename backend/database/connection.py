from contextlib import contextmanager

from mysql.connector import pooling

from config.settings import Config

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="clinica_pool",
            pool_size=5,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
    return _pool


@contextmanager
def get_db():
    """
    Uso:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            ...

    - Commit automático ao sair sem erro.
    - Rollback automático se ocorrer qualquer exceção.
    - Conexão devolvida ao pool em qualquer caso.
    """
    conn = _get_pool().get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
