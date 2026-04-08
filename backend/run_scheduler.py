import logging
import json
import os
import socket
import signal
import time
from datetime import UTC, datetime
from pathlib import Path

import mysql.connector

from config.settings import Config
from services.scheduler import descrever_jobs_scheduler, iniciar_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
_RUNNING = True
_LOCK_NAME = os.getenv("SCHEDULER_LOCK_NAME", "whatsapp-clinica-bot:scheduler")
_LOCK_HEARTBEAT_SECONDS = max(1, int(os.getenv("SCHEDULER_LOCK_HEARTBEAT_SECONDS", "5")))
_HEALTH_FILE_PATH = Path(os.getenv("SCHEDULER_HEALTH_FILE", "/tmp/whatsapp-clinica-bot-scheduler-health.json"))
_lock_conn = None
_lock_connection_id = None


def _stop(*_args):
    global _RUNNING
    _RUNNING = False


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _write_health_snapshot(*, status: str, lock_acquired: bool, scheduler_running: bool, extra: dict | None = None) -> None:
    payload = {
        "status": status,
        "app_role": os.getenv("APP_ROLE", "web"),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "lock_name": _LOCK_NAME,
        "lock_acquired": lock_acquired,
        "scheduler_running": scheduler_running,
        "heartbeat_at": _iso_now(),
        "jobs": descrever_jobs_scheduler(),
    }
    if extra:
        payload.update(extra)

    try:
        _HEALTH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HEALTH_FILE_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Falha ao atualizar arquivo de health do scheduler.")


def _acquire_scheduler_lock() -> bool:
    global _lock_conn, _lock_connection_id
    logger.info("Tentando adquirir lock exclusivo do scheduler - lock=%s host=%s db=%s", _LOCK_NAME, Config.DB_HOST, Config.DB_NAME)
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
        logger.warning("Lock do scheduler indisponivel - lock=%s", _LOCK_NAME)
        return False
    _lock_connection_id = int(row[0])
    logger.info("Lock do scheduler adquirido - lock=%s connection_id=%s", _LOCK_NAME, _lock_connection_id)
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
        logger.info("Lock do scheduler liberado - lock=%s", _LOCK_NAME)
    except Exception:
        logger.exception("Erro ao liberar lock do scheduler.")
    finally:
        _lock_conn.close()
        _lock_conn = None
        _lock_connection_id = None


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    app_role = os.getenv("APP_ROLE", "web")
    logger.info("Entrypoint do scheduler iniciado - app_role=%s pid=%s heartbeat=%ss health_file=%s", app_role, os.getpid(), _LOCK_HEARTBEAT_SECONDS, _HEALTH_FILE_PATH)
    _write_health_snapshot(
        status="starting",
        lock_acquired=False,
        scheduler_running=False,
        extra={"message": "Processo scheduler iniciado e aguardando lock."},
    )

    if not _acquire_scheduler_lock():
        _write_health_snapshot(
            status="standby",
            lock_acquired=False,
            scheduler_running=False,
            extra={"message": "Outro processo ja possui o lock do scheduler."},
        )
        logger.warning("Scheduler nao iniciado: outro processo ja possui o lock '%s'.", _LOCK_NAME)
        raise SystemExit(0)

    iniciar_scheduler()
    _write_health_snapshot(
        status="running",
        lock_acquired=True,
        scheduler_running=True,
        extra={"message": "Scheduler dedicado iniciado com sucesso."},
    )
    logger.info("Scheduler iniciado em processo dedicado e pronto para executar jobs.")

    exit_code = 0
    try:
        while _RUNNING:
            if not _scheduler_lock_healthy():
                _write_health_snapshot(
                    status="unhealthy",
                    lock_acquired=False,
                    scheduler_running=False,
                    extra={"message": "Lock do scheduler perdido; encerrando processo."},
                )
                logger.error("Encerrando scheduler: lock do MySQL perdido.")
                exit_code = 1
                break
            _write_health_snapshot(
                status="running",
                lock_acquired=True,
                scheduler_running=True,
            )
            time.sleep(_LOCK_HEARTBEAT_SECONDS)
    finally:
        shutdown_scheduler()
        _release_scheduler_lock()
        _write_health_snapshot(
            status="stopped",
            lock_acquired=False,
            scheduler_running=False,
            extra={"message": "Scheduler encerrado."},
        )
        logger.info("Scheduler finalizado.")

    raise SystemExit(exit_code)
