import logging
from datetime import date, datetime

from database.connection import get_db
from database.mensagens import salvar_log_whatsapp
from services.whatsapp import send_whatsapp_message
from utils.helpers import timedelta_para_hhmm

logger = logging.getLogger(__name__)


def listar_consultas_do_dia(data_ref: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                c.id,
                c.tipo_consulta,
                c.data,
                c.horario,
                c.status,
                cli.nome,
                cli.sexo,
                cli.telefone,
                m.id       AS medico_id,
                m.nome     AS medico_nome,
                m.telefone AS medico_telefone
            FROM consultas c
            JOIN clientes cli ON cli.id  = c.cliente_id
            JOIN medicos   m  ON m.id    = c.medico_id
            WHERE c.data   = %s
              AND c.status IN ('aguardando_pagamento', 'confirmado')
              AND m.ativo  = TRUE
            ORDER BY c.horario
            """,
            (data_ref,),
        )
        return cursor.fetchall()


def montar_resumo_do_dia(consultas: list[dict], data_ref: str) -> str:
    data_fmt = datetime.strptime(data_ref, "%Y-%m-%d").strftime("%d/%m/%Y")

    if not consultas:
        return f"Bom dia.\n\nNão há consultas agendadas para hoje ({data_fmt})."

    linhas = [f"Bom dia, {consultas[0]['medico_nome']}.", "", f"Consultas de hoje - {data_fmt}", ""]

    for i, c in enumerate(consultas, start=1):
        tipo = "Primeira consulta" if c["tipo_consulta"] == "primeira_consulta" else "Retorno"
        linhas.append(
            f"{i}) {timedelta_para_hhmm(c['horario'])} - "
            f"{c['nome'] or 'Não informado'} - "
            f"{c['telefone']} - "
            f"{c['sexo'] or 'não informado'} - "
            f"{tipo}"
        )

    return "\n".join(linhas)


def enviar_resumo_das_06() -> dict | None:
    hoje = date.today().isoformat()
    consultas = listar_consultas_do_dia(hoje)

    if not consultas:
        return None

    telefone_medico = consultas[0]["medico_telefone"]
    resultado = send_whatsapp_message(telefone_medico, montar_resumo_do_dia(consultas, hoje))

    message_id = None
    mensagens = resultado.get("response", {}).get("messages")
    if mensagens:
        message_id = mensagens[0].get("id")

    salvar_log_whatsapp(
        telefone_destino=telefone_medico,
        tipo_mensagem="resumo_dia_medico",
        message_id=message_id,
        status_envio="enviado",
        payload=resultado.get("payload"),
        resposta_api=resultado.get("response"),
    )
    return resultado


def buscar_detalhes_consulta(telefone: str, data_ref: str, horario: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                c.id,
                c.tipo_consulta,
                c.data,
                c.horario,
                cli.nome,
                cli.sexo,
                cli.telefone,
                m.nome     AS medico_nome,
                m.telefone AS medico_telefone
            FROM consultas c
            JOIN clientes cli ON cli.id = c.cliente_id
            JOIN medicos   m  ON m.id   = c.medico_id
            WHERE cli.telefone = %s
              AND c.data       = %s
              AND c.horario    = %s
              AND c.status IN ('aguardando_pagamento', 'confirmado')
            LIMIT 1
            """,
            (telefone, data_ref, f"{horario}:00"),
        )
        return cursor.fetchone()


def avisar_medico_nova_consulta_hoje(
    telefone: str, data_ref: str, horario: str
) -> dict | None:
    if str(data_ref) != date.today().isoformat():
        return None

    consulta = buscar_detalhes_consulta(telefone, data_ref, horario)
    if not consulta:
        return None

    tipo = "Primeira consulta" if consulta["tipo_consulta"] == "primeira_consulta" else "Retorno"
    mensagem = (
        "Nova consulta agendada para hoje.\n\n"
        f"Nome: {consulta['nome'] or 'Não informado'}\n"
        f"Telefone: {consulta['telefone']}\n"
        f"Sexo: {consulta['sexo'] or 'não informado'}\n"
        f"Tipo: {tipo}\n"
        f"Horário: {timedelta_para_hhmm(consulta['horario'])}"
    )

    resultado = send_whatsapp_message(consulta["medico_telefone"], mensagem)

    message_id = None
    mensagens = resultado.get("response", {}).get("messages")
    if mensagens:
        message_id = mensagens[0].get("id")

    salvar_log_whatsapp(
        telefone_destino=consulta["medico_telefone"],
        tipo_mensagem="nova_consulta_medico",
        message_id=message_id,
        consulta_id=consulta["id"],
        status_envio="enviado",
        payload=resultado.get("payload"),
        resposta_api=resultado.get("response"),
    )
    return resultado