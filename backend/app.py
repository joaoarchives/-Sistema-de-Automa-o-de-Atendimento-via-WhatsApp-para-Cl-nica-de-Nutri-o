import hashlib
import hmac
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services.bot_response import BotResponse
from database.mensagens import atualizar_status_whatsapp, salvar_log_whatsapp
from database.estados import get_estado
from database.runtime_guards import register_processed_webhook_message
from services.bot import processar_comprovante, processar_mensagem
from services.whatsapp import send_whatsapp_interactive_list, send_whatsapp_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
BACKEND_ASSETS = BASE_DIR / "backend" / "assets"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")}})

from api import api as api_blueprint

app.register_blueprint(api_blueprint)

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
WEBHOOK_APP_SECRET = (
    os.getenv("WHATSAPP_APP_SECRET")
    or os.getenv("WEBHOOK_APP_SECRET")
    or os.getenv("META_APP_SECRET")
    or os.getenv("META_WEBHOOK_SECRET")
    or ""
).strip()

logger.info(
    "Webhook secrets carregados - WHATSAPP_APP_SECRET=%s WEBHOOK_APP_SECRET=%s META_APP_SECRET=%s META_WEBHOOK_SECRET=%s secret_efetivo=%s tamanho=%s DEBUG_SECRET_TEST=%r",
    bool((os.getenv("WHATSAPP_APP_SECRET") or "").strip()),
    bool((os.getenv("WEBHOOK_APP_SECRET") or "").strip()),
    bool((os.getenv("META_APP_SECRET") or "").strip()),
    bool((os.getenv("META_WEBHOOK_SECRET") or "").strip()),
    bool(WEBHOOK_APP_SECRET),
    len(WEBHOOK_APP_SECRET),
    os.getenv("DEBUG_SECRET_TEST"),
)


def _validar_assinatura_webhook(raw_body: bytes) -> tuple[bool, str]:
    if not WEBHOOK_APP_SECRET:
        return False, "missing_secret"

    assinatura_recebida = request.headers.get("X-Hub-Signature-256", "").strip()
    if not assinatura_recebida.startswith("sha256="):
        return False, "invalid_signature"

    assinatura_recebida = assinatura_recebida.split("=", 1)[1].strip()
    if not assinatura_recebida:
        return False, "invalid_signature"

    assinatura_esperada = hmac.new(
        WEBHOOK_APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(assinatura_esperada, assinatura_recebida):
        return False, "invalid_signature"

    return True, "ok"


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info("GET /webhook - mode=%s", mode)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        response = app.make_response(challenge)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response, 200

    logger.warning("Webhook verification failed - token mismatch")
    return "Verification token mismatch", 403


@app.post("/webhook")
def receive_webhook():
    raw_body = request.get_data(cache=True) or b""
    assinatura_valida, motivo_assinatura = _validar_assinatura_webhook(raw_body)
    if not assinatura_valida:
        if motivo_assinatura == "missing_secret":
            logger.error("Webhook recusado: segredo de assinatura não configurado.")
            return jsonify({"status": "error", "erro": "Assinatura do webhook não configurada"}), 503
        logger.warning("Webhook recusado por assinatura inválida.")
        return jsonify({"status": "forbidden", "erro": "Assinatura inválida"}), 403

    body = request.get_json(silent=True) or {}

    try:
        entries = body.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                for message in value.get("messages", []):
                    from_number = message.get("from")
                    msg_type = message.get("type")
                    msg_id = message.get("id", "")

                    if msg_id and not register_processed_webhook_message(msg_id):
                        logger.info("Mensagem duplicada ignorada - id=%s", msg_id)
                        continue

                    logger.info("Mensagem recebida - de=%s tipo=%s id=%s", from_number, msg_type, msg_id)

                    if msg_type in {"image", "document"}:
                        salvar_log_whatsapp(
                            telefone_destino=from_number,
                            tipo_mensagem=msg_type,
                            message_id=msg_id,
                            status_envio="recebido",
                            payload=message,
                            resposta_api={},
                        )
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

                    salvar_log_whatsapp(
                        telefone_destino=from_number,
                        tipo_mensagem=msg_type,
                        message_id=msg_id,
                        status_envio="recebido",
                        payload=message,
                        resposta_api={},
                    )

                    try:
                        resposta = processar_mensagem(from_number, texto)
                    except Exception:
                        logger.exception(
                            "Erro ao processar mensagem do bot - de=%s tipo=%s id=%s texto=%r",
                            from_number,
                            msg_type,
                            msg_id,
                            texto[:120],
                        )
                        continue

                    logger.info(
                        "Resposta do bot gerada - de=%s tipo_resposta=%s texto_vazio=%s",
                        from_number,
                        getattr(resposta, "tipo", "texto"),
                        not bool((getattr(resposta, "texto", "") or "").strip()),
                    )

                    if not resposta.texto:
                        logger.info(
                            "Webhook sem envio de texto direto - de=%s motivo=resposta_vazia",
                            from_number,
                        )
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
                        logger.error("Falha ao enviar mensagem WhatsApp - de=%s erro=%s", from_number, e)
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
                    message_id = status.get("id")
                    status_envio = status.get("status")
                    logger.info("Status atualizado - id=%s status=%s", message_id, status_envio)
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
    if FRONTEND_ASSETS.exists():
        arquivo_front = FRONTEND_ASSETS / filename
        if arquivo_front.exists() and arquivo_front.is_file():
            return send_from_directory(FRONTEND_ASSETS, filename)

    if BACKEND_ASSETS.exists():
        arquivo_back = BACKEND_ASSETS / filename
        if arquivo_back.exists() and arquivo_back.is_file():
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
