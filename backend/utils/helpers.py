import json
from datetime import date, datetime

from utils.time_utils import local_today


def timedelta_para_hhmm(valor) -> str:
    """Converte TIME do MySQL (timedelta ou datetime.time) para 'HH:MM'."""
    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M")
    total = int(valor.total_seconds())
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


def gerar_horarios(periodo: str, tipo_consulta: str = "primeira_consulta") -> list[str]:
    """
    Retorna os horários disponíveis para um período e tipo de consulta.

    Manhã:  09:00 – 11:00 (primeira consulta) | 09:00 – 11:30 (retorno)
    Tarde:  16:00 – 18:00 (primeira consulta) | 16:00 – 18:30 (retorno)

    Primeira consulta dura 60 min → último início deixa 1h antes do fim.
    Retorno dura 30 min           → último início deixa 30min antes do fim.
    """
    limites = {
        "manha": {
            "primeira_consulta": (9, 0, 11, 0),
            "retorno": (9, 0, 11, 30),
        },
        "tarde": {
            "primeira_consulta": (16, 0, 18, 0),
            "retorno": (16, 0, 18, 30),
        },
    }
    tipo_key = tipo_consulta if tipo_consulta in ("primeira_consulta", "retorno") else "primeira_consulta"
    h_ini, m_ini, h_fim, m_fim = limites[periodo][tipo_key]

    horarios = []
    hora, minuto = h_ini, m_ini
    while (hora, minuto) <= (h_fim, m_fim):
        horarios.append(f"{hora:02d}:{minuto:02d}")
        minuto += 30
        if minuto == 60:
            minuto = 0
            hora += 1
    return horarios


def json_dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def json_loads(data: str) -> dict:
    if not data:
        return {}
    return json.loads(data)


def _resolver_data(data_str: str) -> date:
    dia, mes = map(int, data_str.split("/"))
    hoje = local_today()
    data_resolvida = date(hoje.year, mes, dia)
    if data_resolvida < hoje:
        data_resolvida = date(hoje.year + 1, mes, dia)
    return data_resolvida


def data_valida(data_str: str) -> bool:
    try:
        _resolver_data(data_str)
        return True
    except ValueError:
        return False


def formatar_data_iso(data_str: str) -> str:
    return _resolver_data(data_str).strftime("%Y-%m-%d")


def formatar_data_br(data_iso: str) -> str:
    return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m")
