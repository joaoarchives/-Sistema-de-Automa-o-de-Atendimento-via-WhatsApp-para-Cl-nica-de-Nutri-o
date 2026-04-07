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
    buscar_periodo_do_dia,
    buscar_plano_por_codigo,
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
    consulta_id: int | None = None
    horarios_disponiveis: list[str] = field(default_factory=list)
    periodo: str | None = None


def buscar_horarios_disponiveis(
    data: str,
    tipo_consulta: str,
    periodo: str | None = None,
) -> tuple[list[str], str | None]:
    """
    Retorna (horarios_livres, periodo_ativo).
    - Se o dia já tem consulta, usa o período dela.
    - Se o dia está livre, usa o período informado.
    - Se periodo é None e o dia está livre, retorna ([], None) → bot pede período.
    """
    periodo_ativo = buscar_periodo_do_dia(data) or periodo
    if not periodo_ativo:
        return [], None
    ocupados = buscar_horarios_ocupados(data)
    livres = [h for h in gerar_horarios(periodo_ativo, tipo_consulta) if h not in ocupados]
    return livres, periodo_ativo


def cancelar_consulta(telefone: str) -> bool:
    return cancelar_ultima_consulta(telefone)


def confirmar_agendamento(telefone: str, dados: dict) -> ResultadoAgendamento:
    """
    Salva a consulta com status aguardando_pagamento.
    Retorna ResultadoAgendamento com consulta_id em caso de sucesso.
    """
    tipo_consulta = dados["tipo_consulta"]
    periodo       = dados.get("periodo")
    plano_codigo  = dados.get("plano_codigo")

    # Resolve plano_id
    plano_id = None
    if plano_codigo:
        plano = buscar_plano_por_codigo(plano_codigo)
        if plano:
            plano_id = plano["id"]

    if not horario_esta_disponivel(dados["data"], dados["horario"]):
        resultado_horarios = buscar_horarios_disponiveis(dados["data"], tipo_consulta, periodo)
        if isinstance(resultado_horarios, tuple):
            disponiveis, periodo_ativo = resultado_horarios
        else:
            disponiveis = resultado_horarios or []
            periodo_ativo = periodo

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
            periodo=periodo_ativo,
        )

    atualizar_cliente(telefone, dados["nome"], dados.get("sexo"))
    consulta_id = salvar_consulta(
        telefone,
        tipo_consulta,
        dados["data"],
        dados["horario"],
        plano_id=plano_id,
        medico_id=dados.get("medico_id", 1),
    )

    try:
        avisar_medico_nova_consulta_hoje(telefone, dados["data"], dados["horario"])
    except Exception:
        logger.exception("Erro ao enviar notificação ao médico — telefone=%s", telefone)

    return ResultadoAgendamento(
        sucesso=True,
        mensagem="Consulta agendada com sucesso.",
        consulta_id=consulta_id,
    )
