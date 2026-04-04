import logging

from database.mensagens import salvar_log_whatsapp
from services.bot_content import BOAS_VINDAS
from services.whatsapp import (
    DEFAULT_PLANOS_FILENAME,
    resolved_pdf_planos_url,
    send_whatsapp_document,
    send_whatsapp_message,
)


logger = logging.getLogger(__name__)


def _message_id_from_response(response_data: dict) -> str | None:
    messages = response_data.get("messages") or []
    if not messages:
        return None
    return messages[0].get("id")


def _registrar_envio(telefone: str, tipo_mensagem: str, resultado: dict) -> None:
    response_data = resultado.get("response", {})
    message_id = _message_id_from_response(response_data)

    salvar_log_whatsapp(
        telefone_destino=telefone,
        tipo_mensagem=tipo_mensagem,
        message_id=message_id,
        status_envio="erro" if not message_id else "enviado",
        payload=resultado.get("payload", {}),
        resposta_api=response_data,
    )


def enviar_boas_vindas_iniciais(telefone: str) -> None:
    try:
        resultado = send_whatsapp_message(telefone, BOAS_VINDAS)
        _registrar_envio(telefone, "texto", resultado)
    except Exception:
        logger.exception("Erro ao enviar mensagem de boas-vindas")

    pdf_planos_url = resolved_pdf_planos_url()
    if not pdf_planos_url:
        logger.warning("PDF dos planos nao enviado: nenhuma URL publica disponivel.")
        return

    try:
        resultado = send_whatsapp_document(
            telefone,
            pdf_planos_url,
            DEFAULT_PLANOS_FILENAME,
            "Confira nossos planos ??",
        )
        _registrar_envio(telefone, "documento", resultado)
    except Exception:
        logger.exception("Erro ao enviar PDF dos planos")
