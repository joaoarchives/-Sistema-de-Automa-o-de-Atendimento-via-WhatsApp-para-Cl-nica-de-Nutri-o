"""
Fluxo de conversa do bot.

Estados:
  inicio → menu → plano → tipo_consulta → data → confirmar_data
  → periodo_livre → horario → nome → sexo → confirmacao
  → aguardando_comprovante

Regras de negócio  → agendamento_service.py
Persistência       → database/estados.py
IA                 → services/gemini.py
"""
from datetime import date, datetime

from services.bot_response import BotResponse
from database.clientes import registrar_cliente_se_nao_existir
from database.consultas import buscar_periodo_do_dia, buscar_planos_ativos, buscar_plano_por_codigo
from database.estados import get_estado, set_estado
from services.agendamento_service import (
    ResultadoAgendamento,
    buscar_horarios_disponiveis,
    cancelar_consulta,
    confirmar_agendamento,
)
from services.gemini import interpretar_data, responder_livre
from services.whatsapp import PDF_PLANOS_URL, send_pagamento_instrucoes, send_whatsapp_document
from utils.helpers import data_valida, formatar_data_br, formatar_data_iso

import logging
logger = logging.getLogger(__name__)

_SAUDACOES = {"menu", "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "obg"}

_MENU = (
    "Olá! Seja bem-vindo ao consultório do nutricionista Paulo Jordão. 💪\n\n"
    "Sou a Sofia, sua assistente virtual. Como posso te ajudar?\n\n"
    "1 - Agendar consulta\n"
    "2 - Cancelar consulta\n\n"
    "Ou me faça qualquer pergunta sobre os planos, serviços e nutrição!"
)

_DIAS_PT = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira",
    3: "quinta-feira",  4: "sexta-feira", 5: "sábado", 6: "domingo",
}

_SIM = {"sim", "s", "yes", "1", "ok", "isso", "correto", "certo", "exato", "confirmado"}
_NAO = {"não", "nao", "n", "no", "2", "errado", "incorreto", "outro", "outra", "negativo"}

_PERIODO_LABEL = {
    "manha": "manhã (09:00 às 12:00)",
    "tarde": "tarde (16:00 às 19:00)",
}

_PRE_CONSULTA = (
    "Recomendações pré-consulta do Dr. Paulo:\n\n"
    "Use roupas adequadas para avaliação física.\n"
    "Homens: sunga ou calção.\n"
    "Mulheres: biquíni ou short e top.\n\n"
    "Aguardando a confirmação do pagamento pelo Dr. Paulo. "
    "Em breve você receberá a confirmação. 🙏"
)


def _nome_dia(data_iso: str) -> str:
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        return _DIAS_PT[dt.weekday()]
    except ValueError:
        return "data informada"


def _hoje_str() -> str:
    return date.today().strftime("%d/%m/%Y")


def _hoje_nome() -> str:
    return _DIAS_PT[date.today().weekday()]


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────

def _handle_menu(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem == "1":
        # Envia PDF dos planos (se URL configurada) e pergunta o plano
        if PDF_PLANOS_URL:
            try:
                send_whatsapp_document(
                    telefone,
                    PDF_PLANOS_URL,
                    "Planos_2026.pdf",
                    "Confira nossos planos 👆",
                )
            except Exception:
                logger.exception("Erro ao enviar PDF dos planos")

        planos = buscar_planos_ativos()
        set_estado(telefone, "plano", {"planos": [p["codigo"] for p in planos]})

        linhas = ["Qual plano você tem interesse?\n"]
        for i, p in enumerate(planos, 1):
            linhas.append(f"{i} - {p['nome']}")
        return BotResponse(texto="\n".join(linhas))

    if mensagem == "2":
        cancelada = cancelar_consulta(telefone)
        set_estado(telefone, "menu")
        return BotResponse(texto=(
            "Sua consulta foi cancelada com sucesso."
            if cancelada
            else "Você não possui consulta agendada para cancelar."
        ))

    return BotResponse(texto=responder_livre(mensagem))


def _handle_plano(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    planos = buscar_planos_ativos()

    # Aceita número (1, 2, 3…)
    plano_escolhido = None
    if mensagem.isdigit():
        idx = int(mensagem) - 1
        if 0 <= idx < len(planos):
            plano_escolhido = planos[idx]

    if not plano_escolhido:
        linhas = ["Opção inválida. Escolha um número da lista:\n"]
        for i, p in enumerate(planos, 1):
            linhas.append(f"{i} - {p['nome']}")
        return BotResponse(texto="\n".join(linhas))

    dados["plano_codigo"] = plano_escolhido["codigo"]
    dados["plano_nome"]   = plano_escolhido["nome"]
    dados["plano_adiant"] = float(plano_escolhido["valor_adiantamento"])
    set_estado(telefone, "tipo_consulta", dados)
    return BotResponse(texto="Qual o tipo da consulta?\n1 - Primeira consulta\n2 - Retorno")


def _handle_tipo_consulta(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    tipos = {"1": "primeira_consulta", "2": "retorno"}
    if mensagem not in tipos:
        return BotResponse(texto="Opção inválida. Digite 1 para Primeira consulta ou 2 para Retorno.")

    dados["tipo_consulta"] = tipos[mensagem]
    set_estado(telefone, "data", dados)
    return BotResponse(texto=(
        "Qual data você gostaria? Pode escrever normalmente, "
        "como \"sexta-feira\", \"amanhã\" ou no formato DD/MM."
    ))


def _handle_data(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if data_valida(mensagem):
        data_iso = formatar_data_iso(mensagem)
        data_br  = mensagem[:5]
        nome_dia = _nome_dia(data_iso)
        dados.update({"data_sugerida": data_iso, "data_br": data_br, "nome_dia": nome_dia})
        set_estado(telefone, "confirmar_data", dados)
        return BotResponse(texto=f"{nome_dia.capitalize()}, dia {data_br}? Está correto? Responda sim ou não.")

    resultado = interpretar_data(mensagem, _hoje_str(), _hoje_nome())
    if not resultado.get("sucesso"):
        return BotResponse(texto="Não consegui entender a data. Pode escrever no formato DD/MM? Exemplo: 15/04.")

    data_br  = resultado["data"][:5]
    data_iso = formatar_data_iso(data_br)
    nome_dia = _nome_dia(data_iso)
    dados.update({"data_sugerida": data_iso, "data_br": data_br, "nome_dia": nome_dia})
    set_estado(telefone, "confirmar_data", dados)
    return BotResponse(texto=(
        f"Você mencionou {nome_dia}. "
        f"Está se referindo ao dia {data_br}? "
        f"Responda sim ou não."
    ))


def _handle_confirmar_data(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem in _NAO:
        dados.pop("data_sugerida", None)
        dados.pop("data_br", None)
        dados.pop("nome_dia", None)
        set_estado(telefone, "data", dados)
        return BotResponse(texto="Tudo bem! Digite a data desejada no formato DD/MM ou escreva normalmente.")

    if mensagem not in _SIM:
        return BotResponse(texto=(
            f"{dados['nome_dia'].capitalize()}, dia {dados['data_br']}? Responda sim ou não."
        ))

    dados["data"] = dados.pop("data_sugerida")
    dados.pop("data_br", None)
    dados.pop("nome_dia", None)

    tipo_consulta  = dados["tipo_consulta"]
    periodo_ativo  = buscar_periodo_do_dia(dados["data"])

    if periodo_ativo:
        dados["periodo"] = periodo_ativo
        label = _PERIODO_LABEL[periodo_ativo]
        disponiveis, _ = buscar_horarios_disponiveis(dados["data"], tipo_consulta, periodo_ativo)

        if not disponiveis:
            set_estado(telefone, "data", dados)
            return BotResponse(texto=(
                f"As consultas desse dia são apenas no período da {label}, "
                f"mas não há mais horários disponíveis.\n"
                f"Digite outra data no formato DD/MM."
            ))

        dados["horarios_disponiveis"] = disponiveis
        set_estado(telefone, "horario", dados)
        return BotResponse(texto=f"As consultas desse dia são no período da {label}. Selecione um horário:")

    else:
        set_estado(telefone, "periodo_livre", dados)
        return BotResponse(texto="Qual período você prefere?\n1 - Manhã (09:00 às 12:00)\n2 - Tarde (16:00 às 19:00)")


def _handle_periodo_livre(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    periodos = {"1": "manha", "2": "tarde"}
    if mensagem not in periodos:
        return BotResponse(texto="Opção inválida. Digite 1 para Manhã ou 2 para Tarde.")

    dados["periodo"] = periodos[mensagem]
    disponiveis, _ = buscar_horarios_disponiveis(dados["data"], dados["tipo_consulta"], dados["periodo"])

    if not disponiveis:
        set_estado(telefone, "data", dados)
        return BotResponse(texto="Não há horários disponíveis para essa data nesse período.\nDigite outra data no formato DD/MM.")

    dados["horarios_disponiveis"] = disponiveis
    set_estado(telefone, "horario", dados)
    return BotResponse(texto="Ótimo! Selecione um horário disponível:")


def _handle_horario(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    horarios = dados.get("horarios_disponiveis", [])

    if mensagem in horarios:
        dados["horario"] = mensagem
        set_estado(telefone, "nome", dados)
        return BotResponse(texto="Perfeito. Agora digite seu nome.")

    if mensagem.isdigit():
        idx = int(mensagem) - 1
        if 0 <= idx < len(horarios):
            dados["horario"] = horarios[idx]
            set_estado(telefone, "nome", dados)
            return BotResponse(texto="Perfeito. Agora digite seu nome.")

    return BotResponse(texto="Horário inválido. Por favor, selecione um horário da lista.")


def _handle_nome(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    dados["nome"] = mensagem.title()
    set_estado(telefone, "sexo", dados)
    return BotResponse(texto="Informe seu sexo:\n1 - Masculino\n2 - Feminino\n3 - Outro")


def _handle_sexo(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    opcoes = {"1": "masculino", "2": "feminino", "3": "outro"}
    if mensagem not in opcoes:
        return BotResponse(texto="Opção inválida. Digite:\n1 - Masculino\n2 - Feminino\n3 - Outro")

    dados["sexo"] = opcoes[mensagem]
    tipo_fmt = "Primeira Consulta" if dados["tipo_consulta"] == "primeira_consulta" else "Retorno"

    set_estado(telefone, "confirmacao", dados)
    return BotResponse(texto=(
        f"Confirme os dados da consulta:\n\n"
        f"Plano: {dados.get('plano_nome', '-')}\n"
        f"Tipo: {tipo_fmt}\n"
        f"Nome: {dados['nome']}\n"
        f"Sexo: {dados['sexo']}\n"
        f"Data: {formatar_data_br(dados['data'])}\n"
        f"Horário: {dados['horario']}\n\n"
        f"Digite 1 para confirmar ou 2 para cancelar."
    ))


def _handle_confirmacao(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem == "2":
        set_estado(telefone, "menu")
        return BotResponse(texto="Agendamento cancelado. Digite 1 para agendar ou 2 para cancelar consulta.")

    if mensagem != "1":
        return BotResponse(texto="Opção inválida. Digite 1 para confirmar ou 2 para cancelar.")

    resultado: ResultadoAgendamento = confirmar_agendamento(telefone, dados)

    if resultado.horarios_disponiveis:
        dados.pop("horario", None)
        dados["horarios_disponiveis"] = resultado.horarios_disponiveis
        if resultado.periodo:
            dados["periodo"] = resultado.periodo
        set_estado(telefone, "horario", dados)
        return BotResponse(texto=resultado.mensagem)

    if not resultado.sucesso:
        dados.pop("horario", None)
        set_estado(telefone, "data", dados)
        return BotResponse(texto=resultado.mensagem)

    # Sucesso — salva consulta_id no estado e envia instruções de pagamento
    dados["consulta_id"] = resultado.consulta_id
    set_estado(telefone, "aguardando_comprovante", dados)

    valor_adiant = dados.get("plano_adiant", 0.0)
    try:
        send_pagamento_instrucoes(telefone, valor_adiant)
    except Exception:
        logger.exception("Erro ao enviar instruções de pagamento — telefone=%s", telefone)

    return BotResponse(texto=_PRE_CONSULTA)


def _handle_aguardando_comprovante(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    # Qualquer texto recebido nesse estado é tratado como tentativa de envio
    return BotResponse(texto=(
        "Estamos aguardando o comprovante de pagamento.\n\n"
        "Por favor, envie a imagem do comprovante aqui nesta conversa. 📎"
    ))


# ──────────────────────────────────────────────
# Dispatcher principal
# ──────────────────────────────────────────────

_HANDLERS = {
    "menu":                    _handle_menu,
    "plano":                   _handle_plano,
    "tipo_consulta":           _handle_tipo_consulta,
    "data":                    _handle_data,
    "confirmar_data":          _handle_confirmar_data,
    "periodo_livre":           _handle_periodo_livre,
    "horario":                 _handle_horario,
    "nome":                    _handle_nome,
    "sexo":                    _handle_sexo,
    "confirmacao":             _handle_confirmacao,
    "aguardando_comprovante":  _handle_aguardando_comprovante,
}


def processar_comprovante(telefone: str) -> BotResponse:
    """Chamado quando o webhook recebe uma imagem do cliente."""
    _, dados = get_estado(telefone)
    set_estado(telefone, "aguardando_comprovante", dados)
    return BotResponse(texto=(
        "Comprovante recebido! ✅\n\n"
        + _PRE_CONSULTA
    ))


def processar_mensagem(telefone: str, mensagem: str) -> BotResponse:
    registrar_cliente_se_nao_existir(telefone)
    mensagem = mensagem.strip().lower()
    estado, dados = get_estado(telefone)

    if mensagem in _SAUDACOES or estado == "inicio":
        set_estado(telefone, "menu")
        return BotResponse(texto=_MENU)

    handler = _HANDLERS.get(estado)
    if handler is None:
        set_estado(telefone, "menu")
        return BotResponse(texto=_MENU)

    resposta = handler(telefone, mensagem, dados)

    # Se passou para estado "horario", devolve lista interativa clicável
    novo_estado, novo_dados = get_estado(telefone)
    if novo_estado == "horario" and novo_dados.get("horarios_disponiveis"):
        horarios = novo_dados["horarios_disponiveis"]
        return BotResponse(
            texto=resposta.texto,
            tipo="lista",
            lista_botao="Ver horários",
            lista_secoes=[{
                "title": "Horários disponíveis",
                "rows": [{"id": h, "title": h} for h in horarios],
            }],
        )

    return resposta
