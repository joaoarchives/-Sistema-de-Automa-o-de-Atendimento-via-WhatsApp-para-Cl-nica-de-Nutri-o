import json
from database.connection import get_db


def _json_dump(data: dict | list | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False, default=str)


def _json_load(data: str | dict | list | None) -> dict:
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    try:
        loaded = json.loads(data)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _extrair_texto_payload(payload: dict) -> str:
    if not payload:
        return ""
    body = payload.get("body")
    if isinstance(body, str):
        return body
    text = payload.get("text")
    if isinstance(text, dict):
        text_body = text.get("body")
        if isinstance(text_body, str):
            return text_body
    interactive = payload.get("interactive")
    if isinstance(interactive, dict):
        interactive_body = interactive.get("body")
        if isinstance(interactive_body, dict):
            interactive_text = interactive_body.get("text")
            if isinstance(interactive_text, str):
                return interactive_text
    document = payload.get("document")
    if isinstance(document, dict):
        caption = document.get("caption")
        if isinstance(caption, str):
            return caption
    return ""


def salvar_log_whatsapp(
    telefone_destino: str,
    tipo_mensagem: str,
    message_id: str | None = None,
    consulta_id: int | None = None,
    status_envio: str = "enviado",
    payload: dict | None = None,
    resposta_api: dict | None = None,
) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO mensagens_whatsapp (
                consulta_id, telefone_destino, tipo_mensagem,
                message_id, status_envio, payload, resposta_api
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                consulta_id, telefone_destino, tipo_mensagem, message_id, status_envio,
                _json_dump(payload),
                _json_dump(resposta_api),
            ),
        )


def salvar_mensagem_recebida(
    telefone: str,
    texto: str,
    msg_id: str | None = None,
) -> None:
    """Salva mensagem enviada pelo cliente (direção: recebida)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO mensagens_whatsapp (
                telefone_destino, tipo_mensagem, message_id, status_envio, payload, resposta_api
            )
            VALUES (%s, 'recebida', %s, 'recebido', %s, NULL)
            """,
            (telefone, msg_id, _json_dump({"body": texto})),
        )


def listar_conversas() -> list[dict]:
    """Retorna a última mensagem de cada paciente."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.telefone_destino AS telefone,
                   COALESCE(cl.nome, m.telefone_destino) AS nome,
                   m.tipo_mensagem, m.payload, m.criado_em
            FROM mensagens_whatsapp m
            LEFT JOIN clientes cl ON cl.telefone = m.telefone_destino
            INNER JOIN (
                SELECT telefone_destino, MAX(criado_em) AS ultima
                FROM mensagens_whatsapp GROUP BY telefone_destino
            ) ult ON ult.telefone_destino = m.telefone_destino
                  AND ult.ultima = m.criado_em
            ORDER BY m.criado_em DESC
        """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            payload = _json_load(r["payload"])
            preview = _extrair_texto_payload(payload)
            result.append({
                "telefone":  r["telefone"],
                "nome":      r["nome"],
                "preview":   preview[:60] if preview else "",
                "direcao":   r["tipo_mensagem"],
                "criado_em": r["criado_em"].isoformat() if r["criado_em"] else None,
            })
        return result


def listar_mensagens_paciente(telefone: str) -> list[dict]:
    """Retorna todas as mensagens de um paciente ordenadas por data."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, tipo_mensagem, status_envio, payload, criado_em
            FROM mensagens_whatsapp
            WHERE telefone_destino = %s
            ORDER BY criado_em ASC
        """, (telefone,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            payload = _json_load(r["payload"])
            texto = _extrair_texto_payload(payload)
            result.append({
                "id":        r["id"],
                "direcao":   r["tipo_mensagem"],
                "texto":     texto,
                "status":    r["status_envio"],
                "criado_em": r["criado_em"].isoformat() if r["criado_em"] else None,
            })
        return result


def atualizar_status_whatsapp(
    message_id: str,
    status_envio: str,
    resposta_api: dict | None = None,
) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE mensagens_whatsapp
            SET status_envio = %s, resposta_api = %s
            WHERE message_id = %s
            """,
            (
                status_envio,
                _json_dump(resposta_api),
                message_id,
            ),
        )
