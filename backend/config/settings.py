import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "clinica")
    DB_CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", "10"))
    DB_POOL_ACQUIRE_TIMEOUT = float(os.getenv("DB_POOL_ACQUIRE_TIMEOUT", "3"))
    DB_POOL_ACQUIRE_RETRY_INTERVAL = float(os.getenv("DB_POOL_ACQUIRE_RETRY_INTERVAL", "0.05"))
    _threads = max(1, int(os.getenv("GUNICORN_THREADS", "4")))
    DB_POOL_SIZE = max(4, int(os.getenv("DB_POOL_SIZE", str(_threads + 2))))
    DB_POOL_RESET_SESSION = _as_bool(os.getenv("DB_POOL_RESET_SESSION"), True)
