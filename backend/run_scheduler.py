import logging
import os
import signal
import time

import mysql.connector

from config.settings import Config
from services.scheduler import iniciar_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
_RUNNING = True
_LOCK_NAME = os.getenv("SCHEDULER_LOCK_NAME", "whatsapp-clinica-bot:scheduler")
_LOCK_HEARTBEAT_SECONDS = max(1, int(os.getenv("SCHEDULER_LOCK_HEARTBEAT_SECONDS", "5")))
_lock_conn = None
_lock_connection_id = None


def _stop(*_args):
    global _RUNNING
    _RUNNING = False


def _acquire_scheduler_lock() -> bool:
    global _lock_conn, _lock_connection_id
    _lock_conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    cursor = _lock_conn.cursor()
    cursor.execute("SELECT CONNECTION_ID(), GET_LOCK(%s, %s)", (_LOCK_NAME, 0))
    row = cursor.fetchone()
    if not row or row[1] != 1:
        return False
    _lock_connection_id = int(row[0])
    return True


def _scheduler_lock_healthy() -> bool:
    if _lock_conn is None or _lock_connection_id is None:
        return False

    try:
        _lock_conn.ping(reconnect=False, attempts=1, delay=0)
        cursor = _lock_conn.cursor()
        cursor.execute("SELECT IS_USED_LOCK(%s)", (_LOCK_NAME,))
        row = cursor.fetchone()
        return bool(row and row[0] == _lock_connection_id)
    except Exception:
        logger.exception("Scheduler perdeu a conexao/lock do MySQL.")
        return False


def _release_scheduler_lock() -> None:
    global _lock_conn, _lock_connection_id
    if _lock_conn is None:
        return

    try:
        cursor = _lock_conn.cursor()
        cursor.execute("SELECT RELEASE_LOCK(%s)", (_LOCK_NAME,))
    except Exception:
        logger.exception("Erro ao liberar lock do scheduler.")
    finally:
        _lock_conn.close()
        _lock_conn = None
        _lock_connection_id = None


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if not _acquire_scheduler_lock():
        logger.warning("Scheduler nao iniciado: outro processo ja possui o lock '%s'.", _LOCK_NAME)
        raise SystemExit(0)

    iniciar_scheduler()
    logger.info("Scheduler iniciado em processo dedicado.")

    exit_code = 0
    try:
        while _RUNNING:
            if not _scheduler_lock_healthy():
                logger.error("Encerrando scheduler: lock do MySQL perdido.")
                exit_code = 1
                break
            time.sleep(_LOCK_HEARTBEAT_SECONDS)
    finally:
        shutdown_scheduler()
        _release_scheduler_lock()
        logger.info("Scheduler finalizado.")

    raise SystemExit(exit_code)
