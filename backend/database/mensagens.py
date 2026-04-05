import json

from database.connection import get_db


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
                consulta_id,
                telefone_destino,
                tipo_mensagem,
                message_id,
                status_envio,
                payload,
                resposta_api
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                consulta_id,
                telefone_destino,
                tipo_mensagem,
                message_id,
                status_envio,
                json.dumps(payload, ensure_ascii=False) if payload else None,
                json.dumps(resposta_api, ensure_ascii=False) if resposta_api else None,
            ),
        )


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
            SET status_envio = %s,
                resposta_api = %s
            WHERE message_id = %s
            """,
            (
                status_envio,
                json.dumps(resposta_api, ensure_ascii=False) if resposta_api else None,
                message_id,
            ),
        )
