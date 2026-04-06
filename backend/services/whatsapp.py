import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")

PIX_CHAVE = os.getenv("PIX_CHAVE", "")
CARTAO_LINK = os.getenv("CARTAO_LINK", "")
PDF_PLANOS_URL = os.getenv("PDF_PLANOS_URL", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

CLINICA_MAPS_URL = (
    "https://www.google.com/maps/search/"
    "Rua+da+Contagem,+1985,+Paracatu+MG,+38603-400,+Brasil,+1%C2%BA+andar,+sala+113."
    "/@-17.238,-46.8925,17z?hl=pt-BR&entry=ttu&g_ep=EgoyMDI2MDQwMS4wIKXMDSoASAFQAw%3D%3D"
)
CLINICA_ENDERECO = (
    "Rua da Contagem, 1985, Paracatu MG, 38603-400, Brasil\n"
    "1º andar, sala 113."
)

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PLANOS_PATH = BASE_DIR / "assets" / "Planos 2026.pdf"

_PLACEHOLDER_TOKENS = {"", "token_meta", "seu_token_aqui", "teste", "dummy"}
_PLACEHOLDER_PHONE_IDS = {"", "id_meta", "seu_id_aqui", "teste", "dummy"}


def _base_url() -> str:
    return (
        f"https://graph.facebook.com/"
        f"{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def _is_configured() -> bool:
    return (
        (WHATSAPP_TOKEN or "").strip() not in _PLACEHOLDER_TOKENS
        and (WHATSAPP_PHONE_NUMBER_ID or "").strip() not in _PLACEHOLDER_PHONE_IDS
    )


def get_pdf_planos_url() -> str:
    if PDF_PLANOS_URL:
        return PDF_PLANOS_URL

    if not PDF_PLANOS_PATH.exists():
        return ""

    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}/assets/Planos%202026.pdf"

    if RAILWAY_PUBLIC_DOMAIN:
        return f"https://{RAILWAY_PUBLIC_DOMAIN}/assets/Planos%202026.pdf"

    return ""


def _fake_response(payload: dict) -> dict:
    logger.info("Modo local: envio para WhatsApp ignorado. payload=%s", payload)
    return {
        "payload": payload,
        "response": {
            "mocked": True,
            "message": "Envio ignorado em modo local/sem credenciais válidas.",
        },
    }


def _post_whatsapp(payload: dict, erro_prefixo: str) -> dict:
    if not _is_configured():
        return _fake_response(payload)

    response = requests.post(_base_url(), headers=_headers(), json=payload, timeout=30)
    response_json = response.json()
    if not response.ok:
        raise RuntimeError(f"{erro_prefixo}: {response.status_code} - {response.text}")
    return {"payload": payload, "response": response_json}


def send_whatsapp_message(telefone: str, mensagem: str) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": mensagem},
    }
    return _post_whatsapp(payload, "Erro ao enviar mensagem")


def send_whatsapp_interactive_list(telefone: str, corpo: str, botao: str, secoes: list) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": corpo},
            "action": {"button": botao, "sections": secoes},
        },
    }
    return _post_whatsapp(payload, "Erro ao enviar lista interativa")


def send_whatsapp_document(telefone: str, url: str, nome_arquivo: str, legenda: str = "") -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "document",
        "document": {
            "link": url,
            "filename": nome_arquivo,
            "caption": legenda,
        },
    }
    return _post_whatsapp(payload, "Erro ao enviar documento")


def send_whatsapp_template(telefone: str, template_name: str, components=None) -> dict:
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {"name": template_name, "language": {"code": "pt_BR"}},
    }
    if components:
        payload["template"]["components"] = components
    return _post_whatsapp(payload, "Erro ao enviar template")


def send_pagamento_instrucoes(telefone: str, valor: float) -> dict:
    valor_fmt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    mensagem = (
        f"Para finalizar seu agendamento, solicitamos o adiantamento de R$ {valor_fmt}.\n\n"
        f"Chave PIX: {PIX_CHAVE}\n\n"
        f"Crédito em até 6x: {CARTAO_LINK}\n\n"
        f"Após o pagamento, envie o comprovante aqui nesta conversa."
    )
    return send_whatsapp_message(telefone, mensagem)


def send_localizacao_clinica(telefone: str) -> dict:
    mensagem = (
        "Localização da clínica:\n\n"
        f"{CLINICA_ENDERECO}\n\n"
        f"{CLINICA_MAPS_URL}"
    )
    return send_whatsapp_message(telefone, mensagem)
def send_recomendacoes_pre_consulta(telefone: str) -> dict:
    mensagem = (
        "Recomendações pré-consulta do Dr. Paulo:\n\n"
        "Use roupas adequadas para avaliação física.\n"
        "Homens: sunga ou calção.\n"
        "Mulheres: biquíni ou short e top."
    )
    return send_whatsapp_message(telefone, mensagem)
