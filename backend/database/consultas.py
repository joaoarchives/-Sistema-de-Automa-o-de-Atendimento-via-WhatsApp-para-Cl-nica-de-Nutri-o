from datetime import date, timedelta, datetime
from database.connection import get_db
from utils.helpers import timedelta_para_hhmm


# ── Funções do bot ────────────────────────────────────────────────────────────

def buscar_horarios_ocupados(data: str) -> list[str]:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT horario FROM consultas
            WHERE data = %s
              AND status IN ('aguardando_pagamento', 'confirmado')
        """, (data,))
        return [timedelta_para_hhmm(row["horario"]) for row in cursor.fetchall()]


def buscar_periodo_do_dia(data: str) -> str | None:
    """
    Retorna o período já definido para um dia ('manha' ou 'tarde'),
    determinado pela primeira consulta do dia (aguardando_pagamento ou confirmada).
    Retorna None se o dia está livre.
    """
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT horario FROM consultas
            WHERE data = %s
              AND status IN ('aguardando_pagamento', 'confirmado')
            ORDER BY id ASC LIMIT 1
        """, (data,))
        row = cursor.fetchone()
    if not row:
        return None
    hhmm = timedelta_para_hhmm(row["horario"])
    hora = int(hhmm.split(":")[0])
    return "manha" if hora < 13 else "tarde"


def horario_esta_disponivel(data: str, horario: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id FROM consultas
            WHERE data = %s AND horario = %s
              AND status IN ('aguardando_pagamento', 'confirmado')
            LIMIT 1
        """, (data, f"{horario}:00"))
        return cursor.fetchone() is None


def salvar_consulta(
    telefone: str,
    tipo_consulta: str,
    data: str,
    horario: str,
    plano_id: int | None = None,
    medico_id: int = 1,
) -> int:
    """Salva consulta com status aguardando_pagamento. Retorna o id gerado."""
    expira_em = datetime.now() + timedelta(hours=1)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consultas
                (cliente_id, plano_id, tipo_consulta, data, horario,
                 status, pagamento_expira_em, medico_id)
            SELECT id, %s, %s, %s, %s, 'aguardando_pagamento', %s, %s
            FROM clientes WHERE telefone = %s
        """, (plano_id, tipo_consulta, data, f"{horario}:00",
              expira_em, medico_id, telefone))
        return cursor.lastrowid


def cancelar_ultima_consulta(telefone: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id FROM consultas c
            JOIN clientes cli ON cli.id = c.cliente_id
            WHERE cli.telefone = %s
              AND c.status IN ('aguardando_pagamento', 'confirmado')
            ORDER BY c.id DESC LIMIT 1
        """, (telefone,))
        row = cursor.fetchone()
        if not row:
            return False
        cursor.execute(
            "UPDATE consultas SET status = 'cancelado' WHERE id = %s",
            (row["id"],)
        )
        return True


def buscar_planos_ativos() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, codigo, nome, valor_total, valor_adiantamento
            FROM planos WHERE ativo = 1 ORDER BY id
        """)
        return cursor.fetchall()


def buscar_plano_por_codigo(codigo: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, codigo, nome, valor_total, valor_adiantamento
            FROM planos WHERE codigo = %s AND ativo = 1
        """, (codigo,))
        return cursor.fetchone()


# ── Funções do painel ─────────────────────────────────────────────────────────

def get_consultas_hoje(data_referencia=None):
    data_referencia = data_referencia or date.today()
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                c.id,
                cl.nome,
                cl.telefone,
                c.tipo_consulta,
                p.nome      AS plano,
                c.data,
                CAST(c.horario AS CHAR) AS horario,
                c.status,
                m.nome      AS medico
            FROM consultas c
            JOIN clientes cl ON cl.id = c.cliente_id
            JOIN medicos  m  ON m.id  = c.medico_id
            LEFT JOIN planos p ON p.id = c.plano_id
            WHERE c.data = %s
            ORDER BY c.horario ASC
        """, (data_referencia,))
        return cursor.fetchall()


def get_consultas_semana(data_inicio=None):
    data_inicio = data_inicio or date.today()
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        fim = data_inicio + timedelta(days=7)
        cursor.execute("""
            SELECT
                c.id,
                cl.nome,
                cl.telefone,
                c.tipo_consulta,
                p.nome      AS plano,
                c.data,
                CAST(c.horario AS CHAR) AS horario,
                c.status,
                m.nome      AS medico
            FROM consultas c
            JOIN clientes cl ON cl.id = c.cliente_id
            JOIN medicos  m  ON m.id  = c.medico_id
            LEFT JOIN planos p ON p.id = c.plano_id
            WHERE c.data BETWEEN %s AND %s
            ORDER BY c.data ASC, c.horario ASC
        """, (data_inicio, fim))
        return cursor.fetchall()
    
def get_total_consultas_historico():
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT COUNT(*) AS total
                       FROM consultas
                       WHERE status IN ('concluido', 'cancelado')
                       """)
        row = cursor.fetchone()
        return int(row["total"]) if row else 0

def get_consultas_historico(limit=20, offset=0):
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                c.id,
                cl.nome,
                cl.telefone,
                c.tipo_consulta,
                p.nome      AS plano,
                c.data,
                CAST(c.horario AS CHAR) AS horario,
                c.status,
                m.nome      AS medico
            FROM consultas c
            JOIN clientes cl ON cl.id = c.cliente_id
            JOIN medicos  m  ON m.id  = c.medico_id
            LEFT JOIN planos p ON p.id = c.plano_id
            WHERE c.status IN ('concluido', 'cancelado')
            ORDER BY c.data DESC, c.horario DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = cursor.fetchall()
        for row in rows:
            if 'data' in row and hasattr(row['data'], 'isoformat'):
                row['data'] = row['data'].isoformat()
        return rows


def atualizar_status_consulta(consulta_id: int, novo_status: str, motivo: str | None = None) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE consultas SET status = %s WHERE id = %s
        """, (novo_status, consulta_id))
        return cursor.rowcount > 0
