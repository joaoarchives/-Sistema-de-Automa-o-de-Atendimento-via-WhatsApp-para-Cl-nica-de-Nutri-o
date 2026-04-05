from database.connection import get_db
from utils.helpers import json_dumps, json_loads


def get_estado(telefone: str) -> tuple[str, dict]:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT estado, dados FROM estados_conversa WHERE telefone = %s",
            (telefone,),
        )
        row = cursor.fetchone()

    if row:
        return row["estado"], json_loads(row["dados"])
    return "inicio", {}


def set_estado(telefone: str, estado: str, dados: dict | None = None) -> None:
    if dados is None:
        dados = {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO estados_conversa (telefone, estado, dados)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                estado = VALUES(estado),
                dados   = VALUES(dados)
            """,
            (telefone, estado, json_dumps(dados)),
        )
