import json
from datetime import datetime


def timedelta_para_hhmm(valor) -> str:
    """Converte TIME do MySQL (timedelta ou datetime.time) para 'HH:MM'."""
    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M")
    total = int(valor.total_seconds())
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


def gerar_horarios(periodo: str) -> list[str]:
    limites = {"manha": (7, 11), "tarde": (13, 17)}
    if periodo not in limites:
        return []

    inicio, fim = limites[periodo]
    horarios = []
    hora, minuto = inicio, 0

    while hora < fim or (hora == fim and minuto <= 30):
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


def data_valida(data_str: str) -> bool:
    try:
        dia, mes = map(int, data_str.split("/"))
        hoje = datetime.now()
        data = datetime(hoje.year, mes, dia)
        if data.date() < hoje.date():
            data = datetime(hoje.year + 1, mes, dia)
        return True
    except ValueError:
        return False


def formatar_data_iso(data_str: str) -> str:
    dia, mes = map(int, data_str.split("/"))
    hoje = datetime.now()
    data = datetime(hoje.year, mes, dia)
    if data.date() < hoje.date():
        data = datetime(hoje.year + 1, mes, dia)
    return data.strftime("%Y-%m-%d")


def formatar_data_br(data_iso: str) -> str:
    return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m")
