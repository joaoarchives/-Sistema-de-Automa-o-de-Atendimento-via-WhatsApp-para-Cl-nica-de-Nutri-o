import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from flask import Flask, request, jsonify, send_from_directory
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

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
BACKEND_ASSETS = BASE_DIR / "backend" / "assets"

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")}})

from api import api as api_blueprint
app.register_blueprint(api_blueprint)

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")


@app.get("/webhook")
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info("GET /webhook — mode=%s", mode)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        response = app.make_response(challenge)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response, 200

    logger.warning("Webhook verification failed — token mismatch")
    return "Verification token mismatch", 403


@app.post("/webhook")
def receive_webhook():
    body = request.get_json(silent=True) or {}

    # Cache de IDs já processados para evitar duplicatas (retries do WhatsApp)
    _ids_processados = getattr(receive_webhook, '_ids_cache', set())
    if len(_ids_processados) > 500:
        _ids_processados.clear()
    receive_webhook._ids_cache = _ids_processados

    try:
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for message in value.get("messages", []):
                    from_number = message.get("from")
                    msg_type    = message.get("type")
                    msg_id      = message.get("id", "")

                    # Ignora mensagens duplicadas (retries do WhatsApp)
                    if msg_id and msg_id in _ids_processados:
                        logger.info("Mensagem duplicada ignorada — id=%s", msg_id)
                        continue
                    if msg_id:
                        _ids_processados.add(msg_id)

                    logger.info("Mensagem recebida — de=%s tipo=%s id=%s", from_number, msg_type, msg_id)

                    # Comprovante de pagamento (imagem ou PDF enviado pelo cliente)
                    if msg_type in {"image","document"}:
                        estado_str, _ = get_estado(from_number)
                        if estado_str == "aguardando_comprovante":
                            resposta = processar_comprovante(from_number)
                            resultado = send_whatsapp_message(from_number,str(resposta))
                            salvar_log_whatsapp(
                                telefone_destino=from_number,
                                tipo_mensagem="texto",
                                message_id=resultado.get("response",{}).get("messages",[{}])[0].get("id"),
                                status_envio="enviado",
                                payload=resultado.get("payload",{}),
                                resposta_api=resultado.get("response",{}),
                            )
                        continue

                    # Texto ou lista interativa
                    if msg_type == "text":
                        texto = message.get("text", {}).get("body", "").strip()
                    elif msg_type == "interactive":
                        interactive = message.get("interactive", {})
                        if "list_reply" in interactive:
                            texto = interactive["list_reply"]["id"]
                        elif "button_reply" in interactive:
                            texto = interactive["button_reply"]["id"]
                        else:
                            logger.warning("Interactive sem list_reply/button_reply: %s", interactive)
                            continue
                    else:
                        continue

                    if not (from_number and texto):
                        continue

                    resposta = processar_mensagem(from_number, texto)

                    # BotResponse vazio significa que o bot já enviou tudo diretamente
                    if not resposta.texto:
                        continue

                    try:
                        if resposta.tipo == "lista":
                            resultado = send_whatsapp_interactive_list(
                                from_number,
                                resposta.texto,
                                resposta.lista_botao,
                                resposta.lista_secoes,
                            )
                        else:
                            resultado = send_whatsapp_message(from_number, str(resposta))
                    except RuntimeError as e:
                        logger.error("Falha ao enviar mensagem WhatsApp — de=%s erro=%s", from_number, e)
                        continue

                    response_data = resultado.get("response", {})
                    message_id = None
                    if response_data.get("messages"):
                        message_id = response_data["messages"][0].get("id")

                    salvar_log_whatsapp(
                        telefone_destino=from_number,
                        tipo_mensagem="lista" if resposta.tipo == "lista" else "texto",
                        message_id=message_id,
                        status_envio="erro" if not message_id else "enviado",
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
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

@app.get("/health")
def healthcheck():
    return jsonify({"status": "ok"}), 200

@app.get("/")
def serve_index():
    if FRONTEND_DIST.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({
        "status": "backend-online",
        "frontend": "build não encontrado"
    }), 200


@app.get("/assets/<path:filename>")
def serve_asset(filename):
    if BACKEND_ASSETS.exists():
        arquivo = BACKEND_ASSETS / filename
        if arquivo.exists() and arquivo.is_file():
            return send_from_directory(BACKEND_ASSETS, filename)
    return jsonify({"erro": "Arquivo não encontrado"}), 404


@app.get("/<path:path>")
def serve_frontend(path):
    if FRONTEND_DIST.exists():
        arquivo = FRONTEND_DIST / path
        if arquivo.exists() and arquivo.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"erro": "Rota não encontrada"}), 404
