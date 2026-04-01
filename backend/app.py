import logging
import os

from flask import Flask, request, jsonify
from flask_cors import CORS
from services.bot_response import BotResponse
from database.mensagens import atualizar_status_whatsapp, salvar_log_whatsapp
from database.estados import get_estado
from services.bot import processar_mensagem, processar_comprovante
from services.whatsapp import send_whatsapp_message, send_whatsapp_interactive_list

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")}})

from api import api as api_blueprint
app.register_blueprint(api_blueprint)

from services.scheduler import iniciar_scheduler
iniciar_scheduler()

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")


@app.get("/webhook")
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
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
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for message in value.get("messages", []):
                    from_number = message.get("from")
                    msg_type    = message.get("type")

                    logger.info("Mensagem recebida — de=%s tipo=%s", from_number, msg_type)

                    # Comprovante de pagamento (imagem enviada pelo cliente)
                    if msg_type == "image":
                        estado_str, _ = get_estado(from_number)
                        if estado_str == "aguardando_comprovante":
                            resposta = processar_comprovante(from_number)
                            resultado = send_whatsapp_message(from_number, str(resposta))
                            salvar_log_whatsapp(
                                telefone_destino=from_number,
                                tipo_mensagem="texto",
                                message_id=resultado.get("response", {}).get("messages", [{}])[0].get("id"),
                                status_envio="enviado",
                                payload=resultado.get("payload", {}),
                                resposta_api=resultado.get("response", {}),
                            )
                        continue

                    # Texto ou lista interativa
                    if msg_type == "text":
                        texto = message.get("text", {}).get("body", "").strip()
                    elif msg_type == "interactive":
                        texto = message["interactive"]["list_reply"]["id"]
                    else:
                        continue

                    if not (from_number and texto):
                        continue

                    resposta = processar_mensagem(from_number, texto)

                    if resposta.tipo == "lista":
                        resultado = send_whatsapp_interactive_list(
                            from_number,
                            resposta.texto,
                            resposta.lista_botao,
                            resposta.lista_secoes,
                        )
                    else:
                        resultado = send_whatsapp_message(from_number, str(resposta))

                    response_data = resultado.get("response", {})
                    message_id = None
                    if response_data.get("messages"):
                        message_id = response_data["messages"][0].get("id")

                    salvar_log_whatsapp(
                        telefone_destino=from_number,
                        tipo_mensagem="lista" if resposta.tipo == "lista" else "texto",
                        message_id=message_id,
                        status_envio="enviado",
                        payload=resultado.get("payload", {}),
                        resposta_api=response_data,
                    )

                for status in value.get("statuses", []):
                    message_id  = status.get("id")
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