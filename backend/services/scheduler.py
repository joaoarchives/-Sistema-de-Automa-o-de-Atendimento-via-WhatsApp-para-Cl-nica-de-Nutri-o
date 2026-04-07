import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from database.connection import get_db
from services.notificacoes_medico import enviar_resumo_das_06
from services.whatsapp import send_whatsapp_message
from utils.helpers import timedelta_para_hhmm
from utils.time_utils import APP_TIMEZONE, local_schedule_to_utc, utc_now, utc_now_naive

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone=APP_TIMEZONE)


def expirar_pagamentos_pendentes() -> None:
    """Libera horários cujo prazo de pagamento (1h) expirou."""
    agora = utc_now_naive()
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.id, c.pagamento_expira_em, cli.telefone
            FROM consultas c
            JOIN clientes cli ON cli.id = c.cliente_id
            WHERE c.status = 'aguardando_pagamento'
              AND c.pagamento_expira_em IS NOT NULL
              AND c.pagamento_expira_em <= %s
            """,
            (agora,),
        )
        expiradas = cursor.fetchall()

        for consulta in expiradas:
            cursor.execute(
                "UPDATE consultas SET status = 'cancelado' WHERE id = %s",
                (consulta["id"],),
            )
            logger.info("Consulta %s cancelada por falta de pagamento.", consulta["id"])

            try:
                send_whatsapp_message(
                    consulta["telefone"],
                    "Seu agendamento foi cancelado pois o pagamento não foi confirmado "
                    "dentro de 1 hora.\n\n"
                    "Se desejar reagendar, é só digitar 1. 😊"
                )
            except Exception:
                logger.exception("Erro ao notificar cliente sobre cancelamento - id=%s", consulta["id"])


def verificar_lembretes() -> None:
    agora = utc_now()
    limite = agora + timedelta(minutes=5)

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.id, c.data, c.horario, cli.telefone
            FROM consultas c
            JOIN clientes cli ON cli.id = c.cliente_id
            WHERE c.status           = 'confirmado'
              AND c.lembrete_enviado = 0
            """
        )
        consultas = cursor.fetchall()

        for consulta in consultas:
            horario_ref = consulta["horario"] if hasattr(consulta["horario"], "strftime") else timedelta_para_hhmm(consulta["horario"])
            horario_fmt = consulta["horario"].strftime("%H:%M") if hasattr(consulta["horario"], "strftime") else timedelta_para_hhmm(consulta["horario"])
            data_hora_utc = local_schedule_to_utc(consulta["data"], horario_ref)

            if not (agora <= data_hora_utc <= limite):
                continue

            mensagem = (
                f"Olá! Lembrete da sua consulta com Dr. Paulo Jordão.\n\n"
                f"Data: {consulta['data'].strftime('%d/%m')}\n"
                f"Horário: {horario_fmt}\n\n"
                f"Em caso de necessidade, responda esta mensagem."
            )
            send_whatsapp_message(consulta["telefone"], mensagem)
            cursor.execute(
                "UPDATE consultas SET lembrete_enviado = 1 WHERE id = %s",
                (consulta["id"],),
            )


def iniciar_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        expirar_pagamentos_pendentes,
        "interval",
        minutes=5,
        id="expirar_pagamentos",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        verificar_lembretes,
        "interval",
        minutes=1,
        id="verificar_lembretes",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        enviar_resumo_das_06,
        "cron",
        hour=6,
        minute=0,
        id="enviar_resumo_do_dia",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=600,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
