"""
Regras de negócio de agendamento.

O bot.py só conhece estados e mensagens.
Qualquer decisão sobre consultas, horários e clientes vive aqui.
"""
import logging
from dataclasses import dataclass, field

from database.clientes import atualizar_cliente
from database.consultas import (
    buscar_horarios_ocupados,
    cancelar_ultima_consulta,
    horario_esta_disponivel,
    salvar_consulta,
)
from services.notificacoes_medico import avisar_medico_nova_consulta_hoje
from utils.helpers import gerar_horarios

logger = logging.getLogger(__name__)


@dataclass
class ResultadoAgendamento:
    sucesso: bool
    mensagem: str
    horarios_disponiveis: list[str] = field(default_factory=list)


def buscar_horarios_disponiveis(data: str, periodo: str) -> list[str]:
    """Retorna os horários livres para uma data e período."""
    ocupados = buscar_horarios_ocupados(data, periodo)
    return [h for h in gerar_horarios(periodo) if h not in ocupados]


def cancelar_consulta(telefone: str) -> bool:
    """Cancela a última consulta agendada do paciente. Retorna True se cancelou."""
    return cancelar_ultima_consulta(telefone)


def confirmar_agendamento(telefone: str, dados: dict) -> ResultadoAgendamento:
    """
    Tenta confirmar o agendamento com os dados coletados no fluxo.

    Retorna ResultadoAgendamento com:
    - sucesso=True  → consulta salva, mensagem de confirmação
    - sucesso=False, horarios_disponiveis vazio    → sem vagas, pedir nova data
    - sucesso=False, horarios_disponiveis não vazio → horário roubado, oferecer outros
    """
    if not horario_esta_disponivel(dados["data"], dados["horario"]):
        disponiveis = buscar_horarios_disponiveis(dados["data"], dados["periodo"])

        if not disponiveis:
            return ResultadoAgendamento(
                sucesso=False,
                mensagem=(
                    "Esse horário acabou de ser ocupado e não há mais horários disponíveis.\n"
                    "Digite outra data no formato DD/MM."
                ),
            )

        return ResultadoAgendamento(
            sucesso=False,
            mensagem="Esse horário acabou de ser ocupado. Escolha outro horário:",
            horarios_disponiveis=disponiveis,
        )

    atualizar_cliente(telefone, dados["nome"], dados.get("sexo"))
    salvar_consulta(
        telefone,
        dados["tipo_consulta"],
        dados["data"],
        dados["horario"],
        dados.get("medico_id", 1),
    )

    try:
        avisar_medico_nova_consulta_hoje(telefone, dados["data"], dados["horario"])
    except Exception:
        logger.exception("Erro ao enviar notificação ao médico — telefone=%s", telefone)

    return ResultadoAgendamento(
        sucesso=True,
        mensagem=(
            "Consulta agendada com sucesso.\n\n"
            "Formas de pagamento: PIX ou cartão.\n"
            "Em breve você receberá as orientações pré-consulta."
        ),
    )
