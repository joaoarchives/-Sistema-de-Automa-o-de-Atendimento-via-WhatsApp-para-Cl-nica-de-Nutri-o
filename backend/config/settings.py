import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY            = os.getenv("SECRET_KEY", "")
    WEBHOOK_VERIFY_TOKEN  = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
    WHATSAPP_TOKEN        = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_API_VERSION  = os.getenv("WHATSAPP_API_VERSION", "v23.0")

    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 3306))
    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME     = os.getenv("DB_NAME", "clinica")
