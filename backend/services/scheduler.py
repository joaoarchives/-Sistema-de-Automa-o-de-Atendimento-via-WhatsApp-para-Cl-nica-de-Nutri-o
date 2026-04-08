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
_CANCELAMENTO_POR_EXPIRACAO = "Cancelado automaticamente por expiracao do pagamento"


def expirar_pagamentos_pendentes() -> None:
    """Libera horarios cujo prazo de pagamento (1h) expirou."""
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
                """
                UPDATE consultas
                SET status = 'cancelado',
                    motivo_cancelamento = %s,
                    pagamento_notificacao_em_andamento = 0,
                    pagamento_notificacao_lock_em = NULL
                WHERE id = %s
                """,
                (_CANCELAMENTO_POR_EXPIRACAO, consulta["id"]),
            )
            logger.info("Consulta %s cancelada por falta de pagamento.", consulta["id"])

            try:
                send_whatsapp_message(
                    consulta["telefone"],
                    "Seu agendamento foi cancelado pois o pagamento nao foi confirmado dentro de 1 hora.\n\n"
                    "Se desejar reagendar, e so digitar 1."
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
            WHERE c.status = 'confirmado'
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
                f"Ola! Lembrete da sua consulta com Dr. Paulo Jordao.\n\n"
                f"Data: {consulta['data'].strftime('%d/%m')}\n"
                f"Horario: {horario_fmt}\n\n"
                "Em caso de necessidade, responda esta mensagem."
            )
            send_whatsapp_message(consulta["telefone"], mensagem)
            cursor.execute(
                "UPDATE consultas SET lembrete_enviado = 1 WHERE id = %s",
                (consulta["id"],),
            )


_JOB_DEFINITIONS = (
    {
        "id": "expirar_pagamentos",
        "func": expirar_pagamentos_pendentes,
        "trigger": "interval",
        "kwargs": {"minutes": 5, "replace_existing": True, "coalesce": True, "max_instances": 1, "misfire_grace_time": 120},
    },
    {
        "id": "verificar_lembretes",
        "func": verificar_lembretes,
        "trigger": "interval",
        "kwargs": {"minutes": 1, "replace_existing": True, "coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
    },
    {
        "id": "enviar_resumo_do_dia",
        "func": enviar_resumo_das_06,
        "trigger": "cron",
        "kwargs": {"hour": 6, "minute": 0, "replace_existing": True, "coalesce": True, "max_instances": 1, "misfire_grace_time": 600},
    },
)


def descrever_jobs_scheduler() -> list[dict]:
    descricoes = []
    for definicao in _JOB_DEFINITIONS:
        kwargs = dict(definicao["kwargs"])
        descricoes.append(
            {
                "id": definicao["id"],
                "trigger": definicao["trigger"],
                "kwargs": kwargs,
            }
        )
    return descricoes


def iniciar_scheduler() -> None:
    if scheduler.running:
        logger.info("Scheduler ja estava em execucao; nenhum job adicional sera registrado.")
        return

    logger.info("Inicializando scheduler dedicado - timezone=%s jobs=%s", APP_TIMEZONE, len(_JOB_DEFINITIONS))
    for definicao in _JOB_DEFINITIONS:
        scheduler.add_job(
            definicao["func"],
            definicao["trigger"],
            id=definicao["id"],
            **definicao["kwargs"],
        )
        logger.info(
            "Job registrado no scheduler - id=%s trigger=%s config=%s",
            definicao["id"],
            definicao["trigger"],
            definicao["kwargs"],
        )
    scheduler.start()
    logger.info("Scheduler em execucao com %s job(s) ativos.", len(_JOB_DEFINITIONS))


def shutdown_scheduler() -> None:
    if scheduler.running:
        logger.info("Encerrando scheduler dedicado.")
        scheduler.shutdown(wait=False)
