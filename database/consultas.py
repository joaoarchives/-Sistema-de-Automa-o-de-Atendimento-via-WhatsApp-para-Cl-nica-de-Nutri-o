from datetime import date, timedelta
from database.connection import get_db
from utils.helpers import timedelta_para_hhmm


# ── Funções do bot ────────────────────────────────────────────────────────────

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
        cursor.execute("""
                       SELECT horario FROM consultas
                       WHERE data = %s AND status = 'confirmado'
                         AND horario BETWEEN %s AND %s
                       """, (data, inicio, fim))
        return [timedelta_para_hhmm(row["horario"]) for row in cursor.fetchall()]


def horario_esta_disponivel(data: str, horario: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT id FROM consultas
                       WHERE data = %s AND horario = %s AND status = 'confirmado'
                           LIMIT 1
                       """, (data, f"{horario}:00"))
        return cursor.fetchone() is None


def salvar_consulta(telefone: str, tipo_consulta: str, data: str, horario: str, medico_id: int = 1) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO consultas (cliente_id, tipo_consulta, data, horario, medico_id)
                       SELECT id, %s, %s, %s, %s FROM clientes WHERE telefone = %s
                       """, (tipo_consulta, data, f"{horario}:00", medico_id, telefone))


def cancelar_ultima_consulta(telefone: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT c.id FROM consultas c
                                            JOIN clientes cli ON cli.id = c.cliente_id
                       WHERE cli.telefone = %s AND c.status = 'confirmado'
                       ORDER BY c.id DESC LIMIT 1
                       """, (telefone,))
        row = cursor.fetchone()
        if not row:
            return False
        cursor.execute("UPDATE consultas SET status = 'cancelado' WHERE id = %s", (row["id"],))
        return True


# ── Funções do painel ─────────────────────────────────────────────────────────

def get_consultas_hoje():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT
                           c.id,
                           cl.nome,
                           cl.telefone,
                           c.tipo_consulta,
                           c.data,
                           CAST(c.horario AS CHAR) AS horario,
                           c.status,
                           m.nome AS medico
                       FROM consultas c
                                JOIN clientes cl ON cl.id = c.cliente_id
                                JOIN medicos m ON m.id = c.medico_id
                       WHERE c.data = %s
                       ORDER BY c.horario ASC
                       """, (date.today(),))
        return cursor.fetchall()


def get_consultas_semana():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        hoje = date.today()
        fim = hoje + timedelta(days=7)
        cursor.execute("""
                       SELECT
                           c.id,
                           cl.nome,
                           cl.telefone,
                           c.tipo_consulta,
                           c.data,
                           CAST(c.horario AS CHAR) AS horario,
                           c.status,
                           m.nome AS medico
                       FROM consultas c
                                JOIN clientes cl ON cl.id = c.cliente_id
                                JOIN medicos m ON m.id = c.medico_id
                       WHERE c.data BETWEEN %s AND %s
                       ORDER BY c.data ASC, c.horario ASC
                       """, (hoje, fim))
        return cursor.fetchall()


def get_consultas_historico(limit=20, offset=0):
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT
                           c.id,
                           cl.nome,
                           cl.telefone,
                           c.tipo_consulta,
                           c.data,
                           CAST(c.horario AS CHAR) AS horario,
                           c.status,
                           m.nome AS medico
                       FROM consultas c
                                JOIN clientes cl ON cl.id = c.cliente_id
                                JOIN medicos m ON m.id = c.medico_id
                       WHERE c.data < %s
                       ORDER BY c.data DESC, c.horario DESC
                           LIMIT %s OFFSET %s
                       """, (date.today(), limit, offset))
        return cursor.fetchall()


def atualizar_status_consulta(consulta_id, novo_status, motivo=None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       UPDATE consultas SET status = %s WHERE id = %s
                       """, (novo_status, consulta_id))
        return cursor.rowcount > 0