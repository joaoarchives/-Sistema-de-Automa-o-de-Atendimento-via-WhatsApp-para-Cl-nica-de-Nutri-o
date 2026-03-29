import os
import requests


WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")


def send_whatsapp_message(telefone: str, mensagem: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError(
            "Defina WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID no .env"
        )

    url = (
        f"https://graph.facebook.com/"
        f"{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {
            "body": mensagem
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response_json = response.json()

    if not response.ok:
        raise RuntimeError(
            f"Erro ao enviar mensagem WhatsApp: "
            f"{response.status_code} - {response.text}"
        )

    return {
        "payload": payload,
        "response": response_json
    }

def send_whatsapp_template(telefone: str, template_name: str, components=None):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError(
            "Defina WHATSAPP_TOKEN e WHATSAPP_PHONE_NUMBER_ID no .env"
        )

    url = (
        f"https://graph.facebook.com/"
        f"{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "pt_BR"},
        },
    }

    if components:
        payload["template"]["components"] = components

    response = requests.post(url, headers=headers, json=payload, timeout=30)


    if not response.ok:
        raise RuntimeError(
            f"Erro ao enviar template WhatsApp: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()


