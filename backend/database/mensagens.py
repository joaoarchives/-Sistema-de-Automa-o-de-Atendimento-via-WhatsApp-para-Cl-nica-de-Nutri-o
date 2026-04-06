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


def get_conversas_lista():
    """Retorna lista de contatos com última mensagem e total."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                m.telefone_destino                        AS telefone,
                cli.nome                                  AS nome,
                MAX(m.criado_em)                          AS ultima_mensagem,
                COUNT(*)                                  AS total_mensagens,
                (
                    SELECT tipo_mensagem
                    FROM mensagens_whatsapp
                    WHERE telefone_destino = m.telefone_destino
                    ORDER BY criado_em DESC
                    LIMIT 1
                )                                         AS ultimo_tipo,
                (
                    SELECT payload
                    FROM mensagens_whatsapp
                    WHERE telefone_destino = m.telefone_destino
                    ORDER BY criado_em DESC
                    LIMIT 1
                )                                         AS ultimo_payload
            FROM mensagens_whatsapp m
            LEFT JOIN clientes cli ON cli.telefone = m.telefone_destino
            GROUP BY m.telefone_destino, cli.nome
            ORDER BY ultima_mensagem DESC
        """)
        return cursor.fetchall()


def get_mensagens_por_telefone(telefone: str):
    """Retorna todas as mensagens de um telefone específico."""
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                m.id,
                m.consulta_id,
                m.telefone_destino,
                m.tipo_mensagem,
                m.message_id,
                m.status_envio,
                m.payload,
                m.criado_em
            FROM mensagens_whatsapp m
            WHERE m.telefone_destino = %s
            ORDER BY m.criado_em ASC
        """, (telefone,))
        return cursor.fetchall()
