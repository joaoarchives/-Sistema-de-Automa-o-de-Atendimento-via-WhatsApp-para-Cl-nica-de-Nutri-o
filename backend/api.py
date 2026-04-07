from datetime import date, datetime, timedelta
import json
import jwt
import os
import logging
from pathlib import Path
from functools import wraps

from flask import Blueprint, Response, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from database.consultas import (
    get_consultas_hoje,
    get_consultas_semana,
    get_consultas_historico,
    get_total_consultas_historico,
    atualizar_status_consulta,
)
from database.mensagens import get_conversas_lista, get_mensagens_por_telefone, salvar_log_whatsapp
from database.runtime_guards import clear_login_failures, get_login_rate_limit, register_login_failure
from utils.time_utils import local_today, utc_isoformat, utc_now

api = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
MEDICO_USER = os.getenv("MEDICO_USER", "").strip()
MEDICO_PASS = os.getenv("MEDICO_PASS", "").strip()
MEDICO_PASS_HASH = os.getenv("MEDICO_PASS_HASH", "").strip()
_LEGACY_PASSWORD_HASH = generate_password_hash(MEDICO_PASS) if MEDICO_PASS else ""

_SECRET_PLACEHOLDERS = {"", "chave_secreta", "dev_secret", "sua_chave_secreta", "secret"}
_MAX_LOGIN_ATTEMPTS = int(os.getenv("LOGIN_MAX_TENTATIVAS", "5"))
_LOGIN_BLOCK_MINUTES = int(os.getenv("LOGIN_BLOQUEIO_MINUTOS", "15"))
_MAX_POR_PAGINA = int(os.getenv("HISTORICO_MAX_POR_PAGINA", "100"))


def limpar_row(row):
    resultado = {}
    for k, v in row.items():
        if isinstance(v, date):
            resultado[k] = v.isoformat()
        elif hasattr(v, "seconds"):
            total = int(v.total_seconds())
            h = total // 3600
            m = (total % 3600) // 60
            resultado[k] = f"{h:02d}:{m:02d}"
        else:
            resultado[k] = v
    return resultado


def extrair_texto_payload(payload, fallback=""):
    if not payload:
        return fallback

    interactive = payload.get("interactive", {}) or {}
    list_reply = interactive.get("list_reply", {}) or {}
    button_reply = interactive.get("button_reply", {}) or {}
    interactive_body = interactive.get("body", {}) or {}
    interactive_action = interactive.get("action", {}) or {}

    raw = (
        payload.get("text")
        or payload.get("body")
        or list_reply.get("title")
        or list_reply.get("description")
        or list_reply.get("id")
        or button_reply.get("title")
        or button_reply.get("id")
        or interactive_body.get("text")
        or interactive_action.get("button")
        or (payload.get("image", {}) or {}).get("caption")
        or (payload.get("document", {}) or {}).get("caption")
        or (payload.get("document", {}) or {}).get("filename")
        or (payload.get("template", {}) or {}).get("name")
    )
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("body") or raw.get("text") or fallback
    if raw is not None:
        return str(raw)
    return fallback


def inferir_sender_type(status_envio: str | None) -> str:
    return "client" if status_envio == "recebido" else "bot"


def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.remote_addr or "desconhecido").strip()


def get_password_hash() -> str:
    return MEDICO_PASS_HASH or _LEGACY_PASSWORD_HASH


def auth_configurada() -> bool:
    return (
        SECRET_KEY not in _SECRET_PLACEHOLDERS
        and bool(MEDICO_USER)
        and bool(get_password_hash())
    )


def login_rate_limit_key(usuario: str) -> str:
    return f"{get_client_ip()}|{(usuario or '_anon_').lower()}"


def registrar_envio_whatsapp(telefone: str, resultado: dict, tipo_mensagem: str | None = None) -> None:
    response_data = resultado.get("response", {}) if isinstance(resultado, dict) else {}
    payload = resultado.get("payload", {}) if isinstance(resultado, dict) else {}
    payload_type = payload.get("type")
    tipo = tipo_mensagem or payload_type or "texto"

    if tipo == "text":
        tipo = "texto"
    elif tipo == "interactive":
        tipo = "lista"

    salvar_log_whatsapp(
        telefone_destino=telefone,
        tipo_mensagem=tipo,
        message_id=response_data.get("messages", [{}])[0].get("id"),
        status_envio="erro" if not response_data.get("messages") else "enviado",
        payload=payload,
        resposta_api=response_data,
    )


def envio_whatsapp_sucesso(resultado: dict) -> bool:
    response_data = resultado.get("response", {}) if isinstance(resultado, dict) else {}
    return bool(response_data.get("messages"))


def inferir_file_type(file_name: str, mime_type: str | None, fallback: str) -> str:
    if mime_type and mime_type.startswith("image/"):
        return "image"

    extensao = Path(file_name or "").suffix.lower().lstrip(".")
    if extensao:
        return extensao

    if mime_type and "/" in mime_type:
        return mime_type.split("/", 1)[1].lower()

    return fallback


def extrair_anexos_payload(payload):
    if not isinstance(payload, dict):
        return []

    anexos = []
    msg_type = payload.get("type")

    if msg_type == "image":
        image = payload.get("image", {}) or {}
        media_id = image.get("id")
        mime_type = image.get("mime_type")
        file_name = image.get("filename") or f"imagem-{media_id or 'whatsapp'}.jpg"
        anexos.append({
            "id": media_id or file_name,
            "fileName": file_name,
            "fileType": inferir_file_type(file_name, mime_type, "image"),
            "fileUrl": f"/api/conversas/media/{media_id}" if media_id else image.get("link"),
            "mimeType": mime_type,
            "size": image.get("file_size") or image.get("size"),
        })

    if msg_type == "document":
        document = payload.get("document", {}) or {}
        media_id = document.get("id")
        mime_type = document.get("mime_type")
        file_name = document.get("filename") or f"arquivo-{media_id or 'whatsapp'}"
        anexos.append({
            "id": media_id or file_name,
            "fileName": file_name,
            "fileType": inferir_file_type(file_name, mime_type, "document"),
            "fileUrl": document.get("link") or (f"/api/conversas/media/{media_id}" if media_id else None),
            "mimeType": mime_type,
            "size": document.get("file_size") or document.get("size"),
        })

    return [anexo for anexo in anexos if anexo.get("fileUrl")]


def parse_positive_int_arg(name: str, default: int, *, minimum: int = 1, maximum: int | None = None):
    raw_value = request.args.get(name)
    if raw_value is None or raw_value == "":
        return default, None

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, f"Parâmetro '{name}' inválido. Use um número inteiro."

    if value < minimum:
        return None, f"Parâmetro '{name}' inválido. O mínimo permitido é {minimum}."

    if maximum is not None and value > maximum:
        return None, f"Parâmetro '{name}' inválido. O máximo permitido é {maximum}."

    return value, None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not auth_configurada():
            return jsonify({"erro": "Autenticação do painel não configurada"}), 503
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"erro": "Token não fornecido"}), 401
        token = auth_header.split(" ")[1]
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"erro": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated


@api.route("/auth/login", methods=["POST"])
def login():
    if not auth_configurada():
        logger.error("Tentativa de login com autenticação do painel não configurada.")
        return jsonify({"erro": "Autenticação do painel não configurada"}), 503

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Body inválido"}), 400

    usuario = str(dados.get("usuario", "")).strip()
    senha = str(dados.get("senha", "")).strip()

    if not usuario or not senha:
        return jsonify({"erro": "Usuário e senha são obrigatórios"}), 400

    rate_limit_key = login_rate_limit_key(usuario)
    rate_limit = get_login_rate_limit(rate_limit_key)
    if rate_limit["bloqueado"]:
        return jsonify({
            "erro": "Muitas tentativas de login. Tente novamente em alguns minutos.",
            "bloqueado_ate": utc_isoformat(rate_limit["bloqueado_ate"]) if rate_limit["bloqueado_ate"] else None,
        }), 429

    password_hash = get_password_hash()
    senha_valida = bool(password_hash) and check_password_hash(password_hash, senha)
    if usuario != MEDICO_USER or not senha_valida:
        resultado_bloqueio = register_login_failure(
            rate_limit_key,
            max_tentativas=_MAX_LOGIN_ATTEMPTS,
            janela_bloqueio_minutos=_LOGIN_BLOCK_MINUTES,
        )
        if resultado_bloqueio["bloqueado"]:
            return jsonify({
                "erro": "Muitas tentativas de login. Tente novamente em alguns minutos.",
                "bloqueado_ate": utc_isoformat(resultado_bloqueio["bloqueado_ate"]) if resultado_bloqueio["bloqueado_ate"] else None,
            }), 429
        return jsonify({"erro": "Usuário ou senha incorretos"}), 401

    clear_login_failures(rate_limit_key)

    expiracao = utc_now() + timedelta(hours=8)
    token = jwt.encode(
        {"usuario": usuario, "exp": expiracao},
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify({
        "token": token,
        "expira_em": utc_isoformat(expiracao),
        "usuario": usuario,
    })


@api.route("/consultas/hoje", methods=["GET"])
@token_required
def consultas_hoje():
    status_filtro = request.args.get("status")
    data_param = request.args.get("data")

    try:
        data_referencia = datetime.strptime(data_param, "%Y-%m-%d").date() if data_param else local_today()
    except ValueError:
        return jsonify({"erro": "Parâmetro 'data' inválido. Use YYYY-MM-DD."}), 400

    consultas = [limpar_row(c) for c in get_consultas_hoje(data_referencia)]

    if status_filtro:
        consultas = [c for c in consultas if c["status"] == status_filtro]

    return jsonify({
        "data": data_referencia.isoformat(),
        "total": len(consultas),
        "consultas": consultas,
    })


@api.route("/consultas/semana", methods=["GET"])
@token_required
def consultas_semana():
    inicio_param = request.args.get("inicio")

    try:
        data_inicio = datetime.strptime(inicio_param, "%Y-%m-%d").date() if inicio_param else local_today()
    except ValueError:
        return jsonify({"erro": "Parâmetro 'inicio' inválido. Use YYYY-MM-DD."}), 400

    consultas = [limpar_row(c) for c in get_consultas_semana(data_inicio)]

    agrupado = {}
    for c in consultas:
        d = str(c["data"])
        agrupado.setdefault(d, []).append(c)

    return jsonify({
        "inicio": data_inicio.isoformat(),
        "semana": [
            {"data": data_item, "consultas": lista}
            for data_item, lista in sorted(agrupado.items())
        ]
    })


@api.route("/consultas/historico", methods=["GET"])
@token_required
def consultas_historico():
    pagina, erro_pagina = parse_positive_int_arg("pagina", 1, minimum=1)
    if erro_pagina:
        return jsonify({"erro": erro_pagina}), 400

    por_pagina, erro_por_pagina = parse_positive_int_arg("por_pagina", 20, minimum=1, maximum=_MAX_POR_PAGINA)
    if erro_por_pagina:
        return jsonify({"erro": erro_por_pagina}), 400

    offset = (pagina - 1) * por_pagina

    consultas = [limpar_row(c) for c in get_consultas_historico(limit=por_pagina, offset=offset)]
    total = get_total_consultas_historico()
    paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return jsonify({
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total": total,
        "paginas": paginas,
        "consultas": consultas,
    })


@api.route("/consultas/<int:consulta_id>/concluir", methods=["PATCH"])
@token_required
def concluir_consulta(consulta_id):
    sucesso = atualizar_status_consulta(consulta_id, "concluido")
    if not sucesso:
        return jsonify({"erro": "Consulta não encontrada"}), 404
    return jsonify({
        "mensagem": "Consulta marcada como concluída",
        "id": consulta_id,
        "status": "concluido",
    })


@api.route("/consultas/<int:consulta_id>/cancelar", methods=["PATCH"])
@token_required
def cancelar_consulta(consulta_id):
    dados = request.get_json() or {}
    motivo = dados.get("motivo", "Cancelado pelo painel")

    sucesso = atualizar_status_consulta(consulta_id, "cancelado", motivo=motivo)
    if not sucesso:
        return jsonify({"erro": "Consulta não encontrada"}), 404
    return jsonify({
        "mensagem": "Consulta cancelada",
        "id": consulta_id,
        "status": "cancelado",
        "motivo": motivo,
    })


@api.route("/consultas/<int:consulta_id>/confirmar-pagamento", methods=["PATCH"])
@token_required
def confirmar_pagamento(consulta_id):
    from database.connection import get_db
    from services.whatsapp import send_recomendacoes_pre_consulta, send_whatsapp_message

    sucesso = atualizar_status_consulta(consulta_id, "confirmado")
    avisos = []
    notificacao_enviada = True
    if not sucesso:
        return jsonify({"erro": "Consulta não encontrada"}), 404

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT cli.telefone, c.data, CAST(c.horario AS CHAR) AS horario
                FROM consultas c
                JOIN clientes cli ON cli.id = c.cliente_id
                WHERE c.id = %s
            """, (consulta_id,))
            row = cursor.fetchone()

        if row:
            data_fmt = row["data"].strftime("%d/%m") if hasattr(row["data"], "strftime") else str(row["data"])
            horario_fmt = str(row["horario"])[:5]
            resultado_confirmacao = send_whatsapp_message(
                row["telefone"],
                f"Pagamento confirmado! ✅\n\n"
                f"Sua consulta está agendada para {data_fmt} às {horario_fmt}.\n\n"
                f"Qualquer dúvida, estamos à disposição. Até lá! 💪"
            )
            registrar_envio_whatsapp(row["telefone"], resultado_confirmacao, "texto")
            if not envio_whatsapp_sucesso(resultado_confirmacao):
                notificacao_enviada = False
                avisos.append("A mensagem de confirmação não pôde ser enviada ao paciente.")
            resultado_recomendacoes = send_recomendacoes_pre_consulta(row["telefone"])
            registrar_envio_whatsapp(row["telefone"], resultado_recomendacoes, "texto")
            if not envio_whatsapp_sucesso(resultado_recomendacoes):
                notificacao_enviada = False
                avisos.append("As recomendações pré-consulta não puderam ser enviadas ao paciente.")
            try:
                from database.estados import get_estado, set_estado
                _, dados_atuais = get_estado(row["telefone"])
                dados_atuais["data"] = row["data"].isoformat() if hasattr(row["data"], "isoformat") else str(row["data"])
                dados_atuais["horario"] = horario_fmt
                set_estado(row["telefone"], "consulta_confirmada", dados_atuais)
            except Exception:
                logger.exception("Erro ao atualizar estado da conversa após confirmação do pagamento.")
                notificacao_enviada = False
                avisos.append("O estado da conversa não pôde ser atualizado após a confirmação.")
        else:
            notificacao_enviada = False
            avisos.append("A consulta foi confirmada, mas o telefone do paciente não foi localizado para notificação.")
    except Exception:
        logger.exception("Erro ao notificar cliente após confirmação do pagamento.")
        notificacao_enviada = False
        avisos.append("A consulta foi confirmada, mas houve falha ao notificar o paciente.")

    return jsonify({
        "mensagem": "Pagamento confirmado",
        "id": consulta_id,
        "status": "confirmado",
        "notificacao_enviada": notificacao_enviada,
        "aviso": " ".join(dict.fromkeys(avisos)) if avisos else None,
    })


@api.route("/planos", methods=["GET"])
@token_required
def listar_planos():
    from database.consultas import buscar_planos_ativos
    planos = buscar_planos_ativos()
    return jsonify({"planos": [
        {
            "id": p["id"],
            "codigo": p["codigo"],
            "nome": p["nome"],
            "valor_total": float(p["valor_total"]),
            "valor_adiantamento": float(p["valor_adiantamento"]),
        }
        for p in planos
    ]})


@api.route("/conversas/media/<media_id>", methods=["GET"])
@token_required
def obter_midia_conversa(media_id):
    from services.whatsapp import download_whatsapp_media

    try:
        media = download_whatsapp_media(media_id)
        response = Response(media["content"], mimetype=media["mime_type"])
        response.headers["Content-Disposition"] = f'inline; filename="{media["filename"]}"'
        return response
    except Exception as exc:
        return jsonify({"erro": f"Não foi possível carregar a mídia: {exc}"}), 502


@api.route("/conversas", methods=["GET"])
@token_required
def listar_conversas():
    rows = get_conversas_lista()
    resultado = []
    for r in rows:
        ultimo_payload = None
        if r.get("ultimo_payload"):
            try:
                ultimo_payload = json.loads(r["ultimo_payload"])
            except Exception:
                ultimo_payload = None
        resultado.append({
            "telefone": r["telefone"],
            "nome": r["nome"] or r["telefone"],
            "ultima_mensagem": r["ultima_mensagem"].isoformat() if r["ultima_mensagem"] else None,
            "total_mensagens": r["total_mensagens"],
            "ultimo_tipo": r["ultimo_tipo"],
            "ultimo_payload": ultimo_payload,
            "ultima_previa": extrair_texto_payload(ultimo_payload, r["ultimo_tipo"]),
        })
    return jsonify({"conversas": resultado})


@api.route("/conversas/<telefone>", methods=["GET"])
@token_required
def mensagens_por_telefone(telefone):
    rows = get_mensagens_por_telefone(telefone)
    mensagens = []
    for r in rows:
        payload = None
        if r["payload"]:
            try:
                payload = json.loads(r["payload"])
            except Exception:
                payload = r["payload"]

        texto = None
        if payload:
            raw = (
                payload.get("text")
                or payload.get("body")
                or (payload.get("template", {}) or {}).get("name")
            )
            if isinstance(raw, str):
                texto = raw
            elif isinstance(raw, dict):
                texto = raw.get("body") or raw.get("text") or r["tipo_mensagem"]
            elif raw is not None:
                texto = str(raw)

        sender_type = inferir_sender_type(r["status_envio"])

        mensagens.append({
            "id": r["id"],
            "consulta_id": r["consulta_id"],
            "sender": sender_type,
            "senderType": sender_type,
            "direction": "incoming" if sender_type == "client" else "outgoing",
            "tipo_mensagem": r["tipo_mensagem"],
            "message_id": r["message_id"],
            "status_envio": r["status_envio"],
            "texto": extrair_texto_payload(payload, texto or r["tipo_mensagem"]),
            "attachments": extrair_anexos_payload(payload),
            "payload": payload,
            "timestamp": r["criado_em"].isoformat() if r["criado_em"] else None,
            "criado_em": r["criado_em"].isoformat() if r["criado_em"] else None,
        })
    return jsonify({
        "telefone": telefone,
        "mensagens": mensagens,
        "total": len(mensagens),
    })
