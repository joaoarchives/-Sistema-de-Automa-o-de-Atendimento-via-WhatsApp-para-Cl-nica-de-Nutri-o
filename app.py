import logging
import os

from flask import Flask, request, jsonify

from database.mensagens import atualizar_status_whatsapp, salvar_log_whatsapp
from services.bot import processar_mensagem
from services.whatsapp import send_whatsapp_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info("GET /webhook — mode=%s", mode)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    logger.warning("Webhook verification failed — token mismatch")
    return "Verification token mismatch", 403


@app.post("/webhook")
def receive_webhook():
    body = request.get_json(silent=True) or {}

    try:
        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})

                for message in value.get("messages", []):
                    from_number = message.get("from")
                    msg_type = message.get("type")

                    logger.info("Mensagem recebida — de=%s tipo=%s", from_number, msg_type)

                    if msg_type == "text":
                        texto = message.get("text", {}).get("body", "").strip()

                        if from_number and texto:
                            resposta = processar_mensagem(from_number, texto)
                            resultado = send_whatsapp_message(from_number, resposta)

                            response_data = resultado.get("response", {})
                            payload = resultado.get("payload", {})
                            message_id = None

                            if response_data.get("messages"):
                                message_id = response_data["messages"][0].get("id")

                            salvar_log_whatsapp(
                                telefone_destino=from_number,
                                tipo_mensagem="texto",
                                message_id=message_id,
                                status_envio="enviado",
                                payload=payload,
                                resposta_api=response_data,
                            )

                for status in value.get("statuses", []):
                    message_id = status.get("id")
                    status_envio = status.get("status")

                    logger.info("Status atualizado — id=%s status=%s", message_id, status_envio)

                    if message_id and status_envio:
                        atualizar_status_whatsapp(
                            message_id=message_id,
                            status_envio=status_envio,
                            resposta_api=status,
                        )

        return jsonify({"status": "ok"}), 200

    except Exception:
        logger.exception("Erro no webhook")
        return jsonify({"status": "error"}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
