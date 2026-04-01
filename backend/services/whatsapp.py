import os
import requests

WHATSAPP_TOKEN          = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION    = os.getenv("WHATSAPP_API_VERSION", "v23.0")

PIX_CHAVE   = os.getenv("PIX_CHAVE", "")
CARTAO_LINK = os.getenv("CARTAO_LINK", "")
PDF_PLANOS_URL = os.getenv("PDF_PLANOS_URL", "")   # URL pública do PDF quando disponível


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


def _check_env() -> None:
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError("Defina WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID no .env")


def send_whatsapp_message(telefone: str, mensagem: str) -> dict:
    _check_env()
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": mensagem},
    }
    response = requests.post(_base_url(), headers=_headers(), json=payload, timeout=30)
    response_json = response.json()
    if not response.ok:
        raise RuntimeError(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
    return {"payload": payload, "response": response_json}


def send_whatsapp_interactive_list(telefone: str, corpo: str, botao: str, secoes: list) -> dict:
    _check_env()
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
    response = requests.post(_base_url(), headers=_headers(), json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Erro ao enviar lista interativa: {response.status_code} - {response.text}")
    return {"payload": payload, "response": response.json()}


def send_whatsapp_document(telefone: str, url: str, nome_arquivo: str, legenda: str = "") -> dict:
    """Envia um documento (PDF) via URL pública."""
    _check_env()
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
    response = requests.post(_base_url(), headers=_headers(), json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Erro ao enviar documento: {response.status_code} - {response.text}")
    return {"payload": payload, "response": response.json()}


def send_whatsapp_template(telefone: str, template_name: str, components=None) -> dict:
    _check_env()
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {"name": template_name, "language": {"code": "pt_BR"}},
    }
    if components:
        payload["template"]["components"] = components
    response = requests.post(_base_url(), headers=_headers(), json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Erro ao enviar template: {response.status_code} - {response.text}")
    return {"payload": payload, "response": response.json()}


def send_pagamento_instrucoes(telefone: str, valor: float) -> dict:
    """
    Envia mensagem com as instruções de pagamento (PIX + link cartão).
    valor = adiantamento a ser pago (50% do plano).
    """
    _check_env()
    valor_fmt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    mensagem = (
        f"Para finalizar seu agendamento, solicitamos o adiantamento de R$ {valor_fmt}.\n\n"
        f"Chave PIX: {PIX_CHAVE}\n\n"
        f"Crédito em até 6x: {CARTAO_LINK}\n\n"
        f"Após o pagamento, envie o comprovante aqui nesta conversa."
    )
    return send_whatsapp_message(telefone, mensagem)
