from __future__ import annotations

from datetime import datetime, timedelta

from database.connection import get_db

_TABLES_READY = False


def ensure_runtime_tables() -> None:
    global _TABLES_READY
    if _TABLES_READY:
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                identificador   VARCHAR(255) NOT NULL,
                tentativas      INT NOT NULL DEFAULT 0,
                bloqueado_ate   DATETIME DEFAULT NULL,
                atualizado_em   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (identificador)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_dedup (
                message_id      VARCHAR(255) NOT NULL,
                criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    _TABLES_READY = True


def get_login_rate_limit(identificador: str) -> dict:
    ensure_runtime_tables()

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT tentativas, bloqueado_ate
            FROM auth_login_attempts
            WHERE identificador = %s
            """,
            (identificador,),
        )
        row = cursor.fetchone()

    tentativas = int(row["tentativas"]) if row else 0
    bloqueado_ate = row["bloqueado_ate"] if row else None
    agora = datetime.utcnow()
    if bloqueado_ate and bloqueado_ate <= agora:
        clear_login_failures(identificador)
        return {
            "tentativas": 0,
            "bloqueado": False,
            "bloqueado_ate": None,
        }
    bloqueado = bool(bloqueado_ate and bloqueado_ate > agora)
    return {
        "tentativas": tentativas,
        "bloqueado": bloqueado,
        "bloqueado_ate": bloqueado_ate,
    }


def register_login_failure(
    identificador: str,
    *,
    max_tentativas: int,
    janela_bloqueio_minutos: int,
) -> dict:
    ensure_runtime_tables()

    status = get_login_rate_limit(identificador)
    tentativas = status["tentativas"] + 1
    bloqueado_ate = None
    if tentativas >= max_tentativas:
        bloqueado_ate = datetime.utcnow() + timedelta(minutes=janela_bloqueio_minutos)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO auth_login_attempts (identificador, tentativas, bloqueado_ate)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                tentativas = VALUES(tentativas),
                bloqueado_ate = VALUES(bloqueado_ate)
            """,
            (identificador, tentativas, bloqueado_ate),
        )

    return {
        "tentativas": tentativas,
        "bloqueado": bool(bloqueado_ate),
        "bloqueado_ate": bloqueado_ate,
    }


def clear_login_failures(identificador: str) -> None:
    ensure_runtime_tables()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM auth_login_attempts WHERE identificador = %s",
            (identificador,),
        )


def register_processed_webhook_message(message_id: str, *, ttl_days: int = 7) -> bool:
    if not message_id:
        return True

    ensure_runtime_tables()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM webhook_dedup
            WHERE criado_em < (UTC_TIMESTAMP() - INTERVAL %s DAY)
            """,
            (ttl_days,),
        )
        cursor.execute(
            """
            INSERT IGNORE INTO webhook_dedup (message_id)
            VALUES (%s)
            """,
            (message_id,),
        )
        return cursor.rowcount > 0
