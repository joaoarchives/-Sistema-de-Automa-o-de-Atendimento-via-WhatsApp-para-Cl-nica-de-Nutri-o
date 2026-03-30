from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, timedelta, date, time
import json
import jwt
import os

from database.consultas import (
    get_consultas_hoje,
    get_consultas_semana,
    get_consultas_historico,
    atualizar_status_consulta,
)
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
    """
    Retorna todas as consultas de hoje.
    Query param opcional: ?status=confirmado|pendente|concluido|cancelado
    """
    status_filtro = request.args.get("status")
    consultas = [limpar_row(c) for c in get_consultas_hoje()]

    if status_filtro:
        consultas = [c for c in consultas if c["status"] == status_filtro]

    return jsonify({
        "data": date.today().isoformat(),
        "total": len(consultas),
        "consultas": consultas,
    })


@api.route("/consultas/semana", methods=["GET"])
@token_required
def consultas_semana():
    """
    Retorna consultas dos próximos 7 dias agrupadas por data.
    """
    consultas = [limpar_row(c) for c in get_consultas_semana()]

    agrupado = {}
    for c in consultas:
        d = str(c["data"])
        if d not in agrupado:
            agrupado[d] = []
        agrupado[d].append(c)

    return jsonify({
        "semana": [
            {"data": data, "consultas": lista}
            for data, lista in sorted(agrupado.items())
        ]
    })


@api.route("/consultas/historico", methods=["GET"])
@token_required
def consultas_historico():
    """
    Retorna consultas passadas (anteriores a hoje).
    Query params: ?pagina=1&por_pagina=20
    """
    pagina = int(request.args.get("pagina", 1))
    por_pagina = int(request.args.get("por_pagina", 20))
    offset = (pagina - 1) * por_pagina

    consultas = [limpar_row(c) for c in get_consultas_historico(limit=por_pagina, offset=offset)]

    return jsonify({
        "pagina": pagina,
        "por_pagina": por_pagina,
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
