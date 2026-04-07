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
_lock_conn = None


def _stop(*_args):
    global _RUNNING
    _RUNNING = False


def _acquire_scheduler_lock() -> bool:
    global _lock_conn
    _lock_conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    cursor = _lock_conn.cursor()
    cursor.execute("SELECT GET_LOCK(%s, %s)", (_LOCK_NAME, 0))
    row = cursor.fetchone()
    return bool(row and row[0] == 1)


def _release_scheduler_lock() -> None:
    global _lock_conn
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


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if not _acquire_scheduler_lock():
        logger.warning("Scheduler não iniciado: outro processo já possui o lock '%s'.", _LOCK_NAME)
        raise SystemExit(0)

    iniciar_scheduler()
    logger.info("Scheduler iniciado em processo dedicado.")

    try:
        while _RUNNING:
            time.sleep(1)
    finally:
        shutdown_scheduler()
        _release_scheduler_lock()
        logger.info("Scheduler finalizado.")
