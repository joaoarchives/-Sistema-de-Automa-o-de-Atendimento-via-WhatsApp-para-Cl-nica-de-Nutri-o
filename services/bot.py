"""
Fluxo de conversa do bot.

Responsabilidade única: ler o estado atual, decidir o próximo estado
e devolver a mensagem de resposta ao usuário.

Regras de negócio (horários, agendamento, cancelamento) → agendamento_service.py
Persistência de estado                                   → database/estados.py
"""
from database.clientes import registrar_cliente_se_nao_existir
from database.estados import get_estado, set_estado
from services.agendamento_service import (
    ResultadoAgendamento,
    buscar_horarios_disponiveis,
    cancelar_consulta,
    confirmar_agendamento,
)
from utils.helpers import data_valida, formatar_data_br, formatar_data_iso

_SAUDACOES = {"menu", "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "obg"}

_MENU = (
    "Olá! Bem-vindo à clínica de nutrição.\n\n"
    "Digite:\n"
    "1 - Agendar consulta\n"
    "2 - Cancelar consulta"
)


def _lista_horarios(horarios: list[str]) -> str:
    return "\n".join(f"{i + 1} - {h}" for i, h in enumerate(horarios))


# ──────────────────────────────────────────────
# Handlers — um por estado
# ──────────────────────────────────────────────

def _handle_menu(telefone: str, mensagem: str, dados: dict) -> str:
    if mensagem == "1":
        set_estado(telefone, "tipo_consulta", {})
        return "Qual o tipo da consulta?\n1 - Primeira consulta\n2 - Retorno"

    if mensagem == "2":
        cancelada = cancelar_consulta(telefone)
        set_estado(telefone, "menu")
        return (
            "Sua consulta foi cancelada com sucesso."
            if cancelada
            else "Você não possui consulta agendada para cancelar."
        )

    return "Opção inválida. Digite 1 para agendar ou 2 para cancelar."


def _handle_tipo_consulta(telefone: str, mensagem: str, dados: dict) -> str:
    tipos = {"1": "primeira_consulta", "2": "retorno"}
    if mensagem not in tipos:
        return "Opção inválida. Digite 1 para Primeira consulta ou 2 para Retorno."

    dados["tipo_consulta"] = tipos[mensagem]
    set_estado(telefone, "periodo", dados)
    return "Qual período você deseja?\n1 - Manhã\n2 - Tarde"


def _handle_periodo(telefone: str, mensagem: str, dados: dict) -> str:
    periodos = {"1": "manha", "2": "tarde"}
    if mensagem not in periodos:
        return "Opção inválida. Digite 1 para Manhã ou 2 para Tarde."

    dados["periodo"] = periodos[mensagem]
    set_estado(telefone, "data", dados)
    return "Digite a data desejada no formato DD/MM."


def _handle_data(telefone: str, mensagem: str, dados: dict) -> str:
    if not data_valida(mensagem):
        return "Data inválida. Digite uma data válida no formato DD/MM."

    dados["data"] = formatar_data_iso(mensagem)
    disponiveis = buscar_horarios_disponiveis(dados["data"], dados["periodo"])

    if not disponiveis:
        set_estado(telefone, "data", dados)
        return (
            "Não há horários disponíveis para essa data nesse período.\n"
            "Digite outra data no formato DD/MM."
        )

    dados["horarios_disponiveis"] = disponiveis
    set_estado(telefone, "horario", dados)
    return f"Escolha um horário:\n{_lista_horarios(disponiveis)}"


def _handle_horario(telefone: str, mensagem: str, dados: dict) -> str:
    horarios = dados.get("horarios_disponiveis", [])

    if not mensagem.isdigit():
        return "Digite o número correspondente ao horário."

    indice = int(mensagem) - 1
    if indice < 0 or indice >= len(horarios):
        return "Horário inválido. Escolha um número da lista."

    dados["horario"] = horarios[indice]
    set_estado(telefone, "nome", dados)
    return "Perfeito. Agora digite seu nome."


def _handle_nome(telefone: str, mensagem: str, dados: dict) -> str:
    dados["nome"] = mensagem.title()
    set_estado(telefone, "sexo", dados)
    return "Informe seu sexo:\n1 - Masculino\n2 - Feminino\n3 - Outro"


def _handle_sexo(telefone: str, mensagem: str, dados: dict) -> str:
    opcoes = {"1": "masculino", "2": "feminino", "3": "outro"}
    if mensagem not in opcoes:
        return "Opção inválida. Digite:\n1 - Masculino\n2 - Feminino\n3 - Outro"

    dados["sexo"] = opcoes[mensagem]
    tipo_fmt = (
        "Primeira Consulta"
        if dados["tipo_consulta"] == "primeira_consulta"
        else "Retorno"
    )

    set_estado(telefone, "confirmacao", dados)
    return (
        f"Confirme os dados da consulta:\n\n"
        f"Nome: {dados['nome']}\n"
        f"Sexo: {dados['sexo']}\n"
        f"Tipo: {tipo_fmt}\n"
        f"Data: {formatar_data_br(dados['data'])}\n"
        f"Horário: {dados['horario']}\n\n"
        f"Digite 1 para confirmar ou 2 para cancelar."
    )


def _handle_confirmacao(telefone: str, mensagem: str, dados: dict) -> str:
    if mensagem == "2":
        set_estado(telefone, "menu")
        return "Agendamento cancelado. Digite 1 para agendar ou 2 para cancelar consulta."

    if mensagem != "1":
        return "Opção inválida. Digite 1 para confirmar ou 2 para cancelar."

    resultado: ResultadoAgendamento = confirmar_agendamento(telefone, dados)

    if resultado.sucesso:
        set_estado(telefone, "menu")
        return resultado.mensagem

    # Horário roubado — tem outros disponíveis
    if resultado.horarios_disponiveis:
        dados.pop("horario", None)
        dados["horarios_disponiveis"] = resultado.horarios_disponiveis
        set_estado(telefone, "horario", dados)
        return f"{resultado.mensagem}\n{_lista_horarios(resultado.horarios_disponiveis)}"

    # Sem vagas — pedir nova data
    dados.pop("horario", None)
    set_estado(telefone, "data", dados)
    return resultado.mensagem


# ──────────────────────────────────────────────
# Dispatcher principal
# ──────────────────────────────────────────────

_HANDLERS = {
    "menu":          _handle_menu,
    "tipo_consulta": _handle_tipo_consulta,
    "periodo":       _handle_periodo,
    "data":          _handle_data,
    "horario":       _handle_horario,
    "nome":          _handle_nome,
    "sexo":          _handle_sexo,
    "confirmacao":   _handle_confirmacao,
}


def processar_mensagem(telefone: str, mensagem: str) -> str:
    registrar_cliente_se_nao_existir(telefone)
    mensagem = mensagem.strip().lower()
    estado, dados = get_estado(telefone)

    if mensagem in _SAUDACOES or estado == "inicio":
        set_estado(telefone, "menu")
        return _MENU

    handler = _HANDLERS.get(estado)
    if handler is None:
        set_estado(telefone, "menu")
        return _MENU

    return handler(telefone, mensagem, dados)
