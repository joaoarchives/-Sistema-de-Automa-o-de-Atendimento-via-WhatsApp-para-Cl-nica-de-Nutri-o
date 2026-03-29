from database.connection import get_db
from utils.helpers import timedelta_para_hhmm


def buscar_horarios_ocupados(data: str, periodo: str) -> list[str]:
    limites = {
        "manha": ("07:00:00", "11:30:00"),
        "tarde": ("13:00:00", "17:30:00"),
    }
    if periodo not in limites:
        return []

    inicio, fim = limites[periodo]
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT horario
            FROM consultas
            WHERE data    = %s
              AND status  = 'agendada'
              AND horario BETWEEN %s AND %s
            """,
            (data, inicio, fim),
        )
        return [timedelta_para_hhmm(row["horario"]) for row in cursor.fetchall()]


def horario_esta_disponivel(data: str, horario: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id FROM consultas
            WHERE data    = %s
              AND horario = %s
              AND status  = 'agendada'
            LIMIT 1
            """,
            (data, f"{horario}:00"),
        )
        return cursor.fetchone() is None


def salvar_consulta(
    telefone: str,
    tipo_consulta: str,
    data: str,
    horario: str,
    medico_id: int = 1,
) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        # Busca cliente_id pelo telefone — a FK agora é por ID
        cursor.execute(
            """
            INSERT INTO consultas (cliente_id, tipo_consulta, data, horario, medico_id)
            SELECT id, %s, %s, %s, %s
            FROM clientes
            WHERE telefone = %s
            """,
            (tipo_consulta, data, f"{horario}:00", medico_id, telefone),
        )


def cancelar_ultima_consulta(telefone: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.id
            FROM consultas c
            JOIN clientes cli ON cli.id = c.cliente_id
            WHERE cli.telefone = %s
              AND c.status     = 'agendada'
            ORDER BY c.id DESC
            LIMIT 1
            """,
            (telefone,),
        )
        row = cursor.fetchone()
        if not row:
            return False

        cursor.execute(
            "UPDATE consultas SET status = 'cancelada' WHERE id = %s",
            (row["id"],),
        )
        return True
