from flask import Blueprint, Response, request, jsonify
from functools import wraps
from datetime import datetime, timedelta, date, time
import json
import jwt
import os
from pathlib import Path

from database.consultas import (
    get_consultas_hoje,
    get_consultas_semana,
    get_consultas_historico,
    get_total_consultas_historico,
    atualizar_status_consulta,
)
from database.mensagens import get_conversas_lista, get_mensagens_por_telefone
api = Blueprint("api", __name__, url_prefix="/api")

SECRET_KEY = os.getenv("SECRET_KEY", "chave_secreta")
MEDICO_USER = os.getenv("MEDICO_USER", "drpaulo")
MEDICO_PASS = os.getenv("MEDICO_PASS", "senha123")


# ── Auth ─────────────────────────────────────────────────────────────────────

def limpar_row(row):
    resultado = {}
    for k, v in row.items():
        if isinstance(v, date):
            resultado[k] = v.isoformat()
        elif hasattr(v, 'seconds'):  # timedelta (MySQL TIME)
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

    raw = (
        payload.get("text")
        or payload.get("body")
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


def inferir_sender(status_envio: str | None) -> str:
    return "client" if status_envio == "recebido" else "bot"


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

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
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
    """
    Body: { "usuario": "drpaulo", "senha": "senha123" }
    Retorna: { "token": "...", "expira_em": "..." }
    """
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "Body inválido"}), 400

    usuario = dados.get("usuario", "")
    senha = dados.get("senha", "")

    if usuario != MEDICO_USER or senha != MEDICO_PASS:
        return jsonify({"erro": "Usuário ou senha incorretos"}), 401

    expiracao = datetime.utcnow() + timedelta(hours=8)
    token = jwt.encode(
        {"usuario": usuario, "exp": expiracao},
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify({
        "token": token,
        "expira_em": expiracao.isoformat() + "Z",
        "usuario": usuario,
    })


# ── Consultas ────────────────────────────────────────────────────────────────

@api.route("/consultas/hoje", methods=["GET"])
@token_required
def consultas_hoje():
    status_filtro = request.args.get("status")
    data_param = request.args.get("data")

    try:
        data_referencia = datetime.strptime(data_param, "%Y-%m-%d").date() if data_param else date.today()
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
        data_inicio = datetime.strptime(inicio_param, "%Y-%m-%d").date() if inicio_param else date.today()
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
            {"data": data, "consultas": lista}
            for data, lista in sorted(agrupado.items())
        ]
    })


@api.route("/consultas/historico", methods=["GET"])
@token_required
def consultas_historico():
    pagina = int(request.args.get("pagina", 1))
    por_pagina = int(request.args.get("por_pagina", 20))
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
    """
    Marca uma consulta como concluída.
    """
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
    """
    Cancela uma consulta.
    Body opcional: { "motivo": "Paciente não compareceu" }
    """
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
    """
    Confirma o pagamento de uma consulta aguardando_pagamento → confirmado.
    Envia mensagem de confirmação ao cliente via WhatsApp.
    """
    from database.consultas import atualizar_status_consulta
    from database.connection import get_db
    from services.whatsapp import send_recomendacoes_pre_consulta, send_whatsapp_message

    sucesso = atualizar_status_consulta(consulta_id, "confirmado")
    if not sucesso:
        return jsonify({"erro": "Consulta não encontrada"}), 404

    # Busca telefone do cliente para notificar
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
            send_whatsapp_message(
                row["telefone"],
                f"Pagamento confirmado! ✅\n\n"
                f"Sua consulta está agendada para {data_fmt} às {horario_fmt}.\n\n"
                f"Qualquer dúvida, estamos à disposição. Até lá! 💪"
            )
            send_recomendacoes_pre_consulta(row["telefone"])
            # Atualiza estado do cliente para consulta_confirmada
            try:
                from database.estados import set_estado, get_estado
                _, dados_atuais = get_estado(row["telefone"])
                dados_atuais["data"] = row["data"].isoformat() if hasattr(row["data"], "isoformat") else str(row["data"])
                dados_atuais["horario"] = horario_fmt
                set_estado(row["telefone"], "consulta_confirmada", dados_atuais)
            except Exception:
                pass
    except Exception:
        pass  # Não falha o endpoint se a notificação der erro

    return jsonify({
        "mensagem": "Pagamento confirmado",
        "id": consulta_id,
        "status": "confirmado",
    })


@api.route("/planos", methods=["GET"])
@token_required
def listar_planos():
    """Retorna todos os planos ativos."""
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


# ── Conversas (histórico WhatsApp) ───────────────────────────────────────────

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
    """Lista todos os contatos com data da última mensagem e total."""
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
            "telefone":        r["telefone"],
            "nome":            r["nome"] or r["telefone"],
            "ultima_mensagem": r["ultima_mensagem"].isoformat() if r["ultima_mensagem"] else None,
            "total_mensagens": r["total_mensagens"],
            "ultimo_tipo":     r["ultimo_tipo"],
            "ultima_previa":   extrair_texto_payload(ultimo_payload, r["ultimo_tipo"]),
        })
    return jsonify({"conversas": resultado})


@api.route("/conversas/<telefone>", methods=["GET"])
@token_required
def mensagens_por_telefone(telefone):
    """Retorna todas as mensagens trocadas com um telefone específico."""
    rows = get_mensagens_por_telefone(telefone)
    mensagens = []
    for r in rows:
        payload = None
        if r["payload"]:
            try:
                payload = json.loads(r["payload"])
            except Exception:
                payload = r["payload"]

        # Extrai texto legível do payload quando possível
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

        mensagens.append({
            "id":            r["id"],
            "consulta_id":   r["consulta_id"],
            "sender":        inferir_sender(r["status_envio"]),
            "tipo_mensagem": r["tipo_mensagem"],
            "message_id":    r["message_id"],
            "status_envio":  r["status_envio"],
            "texto":         extrair_texto_payload(payload, texto or r["tipo_mensagem"]),
            "attachments":   extrair_anexos_payload(payload),
            "payload":       payload,
            "timestamp":     r["criado_em"].isoformat() if r["criado_em"] else None,
            "criado_em":     r["criado_em"].isoformat() if r["criado_em"] else None,
        })
    return jsonify({
        "telefone":  telefone,
        "mensagens": mensagens,
        "total":     len(mensagens),
    })
