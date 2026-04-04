"""Fluxo de conversa do bot."""

import logging
from datetime import datetime

from database.clientes import registrar_cliente_se_nao_existir
from database.consultas import buscar_periodo_do_dia, buscar_planos_ativos, buscar_plano_por_codigo
from database.estados import get_estado, set_estado
from services.agendamento_service import (
    ResultadoAgendamento,
    buscar_horarios_disponiveis,
    cancelar_consulta,
    confirmar_agendamento,
)
from services.bot_content import (
    AGRADECIMENTOS,
    DIAS_PT,
    LOCALIZACAO_CLINICA,
    MENU,
    NAO,
    PALAVRAS_COMPROVANTE,
    PALAVRAS_CONFIRMACAO,
    PERIODO_LABEL,
    PRE_CONSULTA,
    SAUDACOES,
    SIM,
    encerramento_menu,
    encerramento_suave,
    hoje_nome,
    hoje_str,
    mensagem_tem_localizacao,
    resposta_localizacao,
)
from services.bot_lists import (
    resposta_lista_confirmacao,
    resposta_lista_horarios,
    resposta_lista_periodo,
    resposta_lista_planos,
    resposta_lista_sexo,
    resposta_lista_tipo_consulta,
)
from services.bot_outbound import enviar_boas_vindas_iniciais
from services.bot_response import BotResponse
from services.gemini import detectar_intencao, interpretar_data, responder_livre
from services.whatsapp import send_pagamento_instrucoes
from utils.helpers import data_valida, formatar_data_br, formatar_data_iso

logger = logging.getLogger(__name__)

def _nome_dia(data_iso: str) -> str:
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        return DIAS_PT[dt.weekday()]
    except ValueError:
        return "data informada"

def _handle_boas_vindas(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    """Estado após a saudação inicial. Usa Gemini para detectar intenção."""

    # Agradecimento/encerramento — responde e mantém no estado

    if mensagem in AGRADECIMENTOS:

        set_estado(telefone, "boas_vindas", dados)

        return BotResponse(texto=(

            "De nada! 😊 Estou por aqui se precisar de mais alguma coisa.\n\n"

            f"{encerramento_menu()}"

        ))

    intencao = detectar_intencao(mensagem)

    if intencao == "agendar":

        set_estado(telefone, "menu")

        return _handle_menu(telefone, "1", {})

    if intencao == "recusar":

        set_estado(telefone, "inicio")

        return BotResponse(texto=(

            "Tudo bem! Se precisar de mais informações ou quiser agendar, é só chamar. "

            "Até logo! 😊"

        ))

    # Dúvida livre — Gemini responde e mantém no estado boas_vindas

    resposta_gemini = responder_livre(mensagem)

    set_estado(telefone, "boas_vindas", dados)

    return BotResponse(texto=(

        f"{resposta_gemini}\n\n"

        f"{encerramento_menu()}"

    ))

def _handle_menu(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem == "1":
        planos = buscar_planos_ativos()
        set_estado(telefone, "plano", {"planos": [p["codigo"] for p in planos]})
        return resposta_lista_planos(planos)

    if mensagem == "2":
        cancelada = cancelar_consulta(telefone)
        set_estado(telefone, "menu")
        return BotResponse(
            texto=(
                "Sua consulta foi cancelada com sucesso. ?"
                if cancelada
                else "Voc? n?o possui consulta agendada para cancelar."
            )
        )

    return BotResponse(texto=responder_livre(mensagem))

def _handle_plano(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    planos = buscar_planos_ativos()

    plano_escolhido = None

    for p in planos:

        if mensagem == p["codigo"]:

            plano_escolhido = p

            break

    if not plano_escolhido and mensagem.isdigit():

        idx = int(mensagem) - 1

        if 0 <= idx < len(planos):

            plano_escolhido = planos[idx]

    if not plano_escolhido:

        return BotResponse(texto="Opção inválida. Por favor, selecione um plano da lista.")

    dados["plano_codigo"] = plano_escolhido["codigo"]

    dados["plano_nome"]   = plano_escolhido["nome"]

    dados["plano_adiant"] = float(plano_escolhido["valor_adiantamento"])

    set_estado(telefone, "tipo_consulta", dados)

    return BotResponse(

        texto="Qual o tipo da consulta? 🩺",

        tipo="lista",

        lista_botao="Selecionar tipo",

        lista_secoes=[{

            "title": "Tipo de consulta",

            "rows": [

                {"id": "1", "title": "Primeira consulta"},

                {"id": "2", "title": "Retorno"},

            ],

        }],

    )

def _handle_tipo_consulta(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    tipos = {"1": "primeira_consulta", "2": "retorno"}

    if mensagem not in tipos:
        return resposta_lista_tipo_consulta("Por favor, selecione o tipo da consulta: ??")

    dados["tipo_consulta"] = tipos[mensagem]
    set_estado(telefone, "data", dados)
    return BotResponse(
        texto=(
            "Qual data voc? gostaria? ?? Pode escrever normalmente, "
            'como "sexta-feira", "amanh?" ou no formato DD/MM.'
        )
    )

def _handle_data(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    if data_valida(mensagem):

        data_iso = formatar_data_iso(mensagem)

        data_br  = mensagem[:5]

        nome_dia = _nome_dia(data_iso)

        dados.update({"data_sugerida": data_iso, "data_br": data_br, "nome_dia": nome_dia})

        set_estado(telefone, "confirmar_data", dados)

        return BotResponse(texto=f"{nome_dia.capitalize()}, dia {data_br}? Está correto? Responda sim ou não. 📅")

    resultado = interpretar_data(mensagem, hoje_str(), hoje_nome())

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

        f"Responda sim ou não. 📅"

    ))

def _handle_confirmar_data(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem in NAO:
        dados.pop("data_sugerida", None)
        dados.pop("data_br", None)
        dados.pop("nome_dia", None)
        set_estado(telefone, "data", dados)
        return BotResponse(texto="Tudo bem! Digite a data desejada no formato DD/MM ou escreva normalmente.")

    if mensagem not in SIM:
        return BotResponse(texto=f"{dados['nome_dia'].capitalize()}, dia {dados['data_br']}? Responda sim ou nao.")

    dados["data"] = dados.pop("data_sugerida")
    dados.pop("data_br", None)
    dados.pop("nome_dia", None)

    tipo_consulta = dados["tipo_consulta"]
    periodo_ativo = buscar_periodo_do_dia(dados["data"])

    if periodo_ativo:
        dados["periodo"] = periodo_ativo
        label = PERIODO_LABEL[periodo_ativo]
        disponiveis, _ = buscar_horarios_disponiveis(dados["data"], tipo_consulta, periodo_ativo)

        if not disponiveis:
            set_estado(telefone, "data", dados)
            return BotResponse(
                texto=(
                    f"As consultas desse dia sao apenas no periodo da {label}, "
                    "mas nao ha mais horarios disponiveis.\n"
                    "Digite outra data no formato DD/MM."
                )
            )

        dados["horarios_disponiveis"] = disponiveis
        set_estado(telefone, "horario", dados)
        return BotResponse(texto=f"As consultas desse dia sao no periodo da {label}. Selecione um horario.")

    set_estado(telefone, "periodo_livre", dados)
    return resposta_lista_periodo("Qual periodo voce prefere?")


def _handle_periodo_livre(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    periodos = {"1": "manha", "2": "tarde"}

    if mensagem not in periodos:
        return resposta_lista_periodo("Por favor, selecione um periodo.")

    dados["periodo"] = periodos[mensagem]
    disponiveis, _ = buscar_horarios_disponiveis(dados["data"], dados["tipo_consulta"], dados["periodo"])

    if not disponiveis:
        set_estado(telefone, "data", dados)
        return BotResponse(
            texto="Nao ha horarios disponiveis para essa data nesse periodo.\nDigite outra data no formato DD/MM."
        )

    dados["horarios_disponiveis"] = disponiveis
    set_estado(telefone, "horario", dados)
    return BotResponse(texto="Otimo! Selecione um horario disponivel.")


def _handle_horario(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    horarios = dados.get("horarios_disponiveis", [])

    if mensagem in horarios:

        dados["horario"] = mensagem

        set_estado(telefone, "nome", dados)

        return BotResponse(texto="Perfeito! ✅ Agora me diga seu nome completo.")

    if mensagem.isdigit():

        idx = int(mensagem) - 1

        if 0 <= idx < len(horarios):

            dados["horario"] = horarios[idx]

            set_estado(telefone, "nome", dados)

            return BotResponse(texto="Perfeito! ✅ Agora me diga seu nome completo.")

    return BotResponse(texto="Horário inválido. Por favor, selecione um horário da lista.")

def _handle_nome(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    dados["nome"] = mensagem.title()
    set_estado(telefone, "sexo", dados)
    return resposta_lista_sexo("Qual o seu sexo?")


def _handle_sexo(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    opcoes = {"1": "masculino", "2": "feminino", "3": "outro"}

    if mensagem not in opcoes:
        return resposta_lista_sexo("Por favor, selecione seu sexo.")

    dados["sexo"] = opcoes[mensagem]
    tipo_fmt = "Primeira Consulta" if dados["tipo_consulta"] == "primeira_consulta" else "Retorno"
    set_estado(telefone, "confirmacao", dados)
    return resposta_lista_confirmacao(
        (
            "Confira os dados da sua consulta:\n\n"
            f"Plano: {dados.get('plano_nome', '-')}\n"
            f"Tipo: {tipo_fmt}\n"
            f"Nome: {dados['nome']}\n"
            f"Sexo: {dados['sexo']}\n"
            f"Data: {formatar_data_br(dados['data'])}\n"
            f"Horario: {dados['horario']}\n\n"
            "Tudo certo?"
        )
    )


def _handle_confirmacao(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem == "2":
        set_estado(telefone, "menu")
        return BotResponse(texto="Agendamento cancelado. Digite 1 para agendar ou 2 para cancelar consulta.")

    if mensagem != "1":
        return resposta_lista_confirmacao("Por favor, confirme ou cancele o agendamento:")

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

    dados["consulta_id"] = resultado.consulta_id
    set_estado(telefone, "aguardando_comprovante", dados)

    valor_adiant = dados.get("plano_adiant", 0.0)
    try:
        send_pagamento_instrucoes(telefone, valor_adiant)
    except Exception:
        logger.exception("Erro ao enviar instrucoes de pagamento - telefone=%s", telefone)

    return BotResponse(texto=f"{PRE_CONSULTA}\n\n{LOCALIZACAO_CLINICA}")


def _handle_aguardando_comprovante(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    # Agradecimento enquanto aguarda — não repete a instrução

    if mensagem in AGRADECIMENTOS:

        return BotResponse(texto=(

            "De nada! 😊\n\n"

            "Assim que o Dr. Paulo confirmar o pagamento, eu te aviso por aqui."

        ))

    return BotResponse(texto=(

        "Estamos aguardando o comprovante de pagamento. 📎\n\n"

        "Por favor, envie a imagem do comprovante aqui nesta conversa."

    ))

def _handle_pagamento_em_analise(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    """Aguardando confirmação do pagamento pelo médico."""

    msg_lower = mensagem.strip().lower()

    if any(p in msg_lower for p in PALAVRAS_CONFIRMACAO):

        return BotResponse(texto=(

            "Ainda estamos aguardando a confirmação do pagamento pelo Dr. Paulo.\n\n"

            "Assim que ele confirmar, eu te aviso por aqui imediatamente. 🙏"

        ))

    if any(p in msg_lower for p in PALAVRAS_COMPROVANTE):

        return BotResponse(texto=(

            "Seu comprovante já foi recebido e está em análise. 🙏\n\n"

            "Agora é só aguardar a confirmação do Dr. Paulo. Assim que ele validar o pagamento, "

            "você receberá uma mensagem aqui na conversa."

        ))

    intencao = detectar_intencao(mensagem)

    if intencao == "recusar":

        # Despedida ou agradecimento — responde com educação

        return BotResponse(texto=(

            "De nada! 😊 Fico feliz em poder ajudar.\n\n"

            "Assim que o Dr. Paulo confirmar o pagamento, eu te aviso por aqui."

        ))

    if intencao == "agendar":

        # Cliente quer agendar outra consulta

        return BotResponse(texto=(

            "Seu comprovante está em análise. 🙏\n\n"

            "Assim que o pagamento for confirmado, ficará tudo certo! "

            "Caso queira agendar outra consulta, é só nos contatar depois."

        ))

    # Dúvida — Gemini responde mas mantém no estado

    resposta_gemini = responder_livre(mensagem)

    set_estado(telefone, "pagamento_em_analise", dados)

    return BotResponse(texto=(

        f"{resposta_gemini}\n\n"

        "Seu comprovante segue em análise. "

        "Assim que o Dr. Paulo confirmar o pagamento, eu te aviso por aqui. 🙏"

    ))

def _handle_consulta_confirmada(telefone: str, mensagem: str, dados: dict) -> BotResponse:

    """Estado após pagamento confirmado pelo médico."""

    if mensagem in AGRADECIMENTOS:

        set_estado(telefone, "consulta_confirmada", dados)

        return BotResponse(texto="De nada! 😊 Nos vemos no dia da consulta. 💪")

    msg_lower = mensagem.strip().lower()

    quer_reagendar = any(kw in msg_lower for kw in _REAGENDAR)

    if quer_reagendar:

        cancelar_consulta(telefone)

        set_estado(telefone, "menu")

        return BotResponse(

            texto=(

                "Tudo bem! Vou cancelar sua consulta atual para você reagendar. 📅\n\n"

                "Lembrando que o valor já pago não é reembolsável, mas será descontado "

                "no novo agendamento conforme combinado com o Dr. Paulo.\n\n"

                "Vamos escolher um novo horário?"

            ),

            tipo="lista",

            lista_botao="Reagendar",

            lista_secoes=[{

                "title": "O que deseja fazer?",

                "rows": [

                    {"id": "1", "title": "📅 Reagendar consulta"},

                    {"id": "2", "title": "❌ Cancelar consulta"},

                ],

            }],

        )

    intencao = detectar_intencao(mensagem)

    if intencao == "agendar":

        cancelar_consulta(telefone)

        set_estado(telefone, "menu")

        return _handle_menu(telefone, "1", {})

    if intencao == "recusar":

        set_estado(telefone, "consulta_confirmada", dados)

        return BotResponse(texto=f"Até logo! {encerramento_suave()}")

    # Dúvida livre — Gemini responde com contexto da consulta

    data_fmt = formatar_data_br(dados.get("data", "")) if dados.get("data") else ""

    horario_fmt = dados.get("horario", "")

    contexto = mensagem

    if data_fmt or horario_fmt:

        contexto = (

            f"[Contexto: cliente com consulta confirmada"

            + (f" para {data_fmt}" if data_fmt else "")

            + (f" às {horario_fmt}" if horario_fmt else "")

            + f"] {mensagem}"

        )

    resposta_gemini = responder_livre(contexto)

    set_estado(telefone, "consulta_confirmada", dados)

    return BotResponse(texto=resposta_gemini)

_HANDLERS = {
    "boas_vindas": _handle_boas_vindas,
    "menu": _handle_menu,
    "plano": _handle_plano,
    "tipo_consulta": _handle_tipo_consulta,
    "data": _handle_data,
    "confirmar_data": _handle_confirmar_data,
    "periodo_livre": _handle_periodo_livre,
    "horario": _handle_horario,
    "nome": _handle_nome,
    "sexo": _handle_sexo,
    "confirmacao": _handle_confirmacao,
    "aguardando_comprovante": _handle_aguardando_comprovante,
    "pagamento_em_analise": _handle_pagamento_em_analise,
    "consulta_confirmada": _handle_consulta_confirmada,
}

# Compatibilidade com testes/mocks antigos do projeto.
interpretar_data_periodo = interpretar_data
_handle_periodo = _handle_periodo_livre

def processar_comprovante(telefone: str) -> BotResponse:

    """Chamado quando o webhook recebe uma imagem ou PDF do cliente."""

    _, dados = get_estado(telefone)

    set_estado(telefone, "pagamento_em_analise", dados)

    return BotResponse(texto=(

        "Comprovante recebido! ✅\n\n"

        "Aguardando a confirmação do pagamento pelo Dr. Paulo. "

        "Em breve você receberá a confirmação. 🙏"

    ))

def processar_mensagem(telefone: str, mensagem: str) -> BotResponse:
    registrar_cliente_se_nao_existir(telefone)
    mensagem = mensagem.strip().lower()

    estado, dados = get_estado(telefone)

    if mensagem_tem_localizacao(mensagem):
        return BotResponse(texto=resposta_localizacao(incluir_encerramento=False))

    if mensagem in SAUDACOES or estado == "inicio":
        set_estado(telefone, "boas_vindas")
        enviar_boas_vindas_iniciais(telefone)
        return BotResponse(texto="")

    handler = _HANDLERS.get(estado)
    if handler is None:
        set_estado(telefone, "menu")
        return BotResponse(texto=MENU)

    resposta = handler(telefone, mensagem, dados)

    novo_estado, novo_dados = get_estado(telefone)
    if novo_estado == "horario" and novo_dados.get("horarios_disponiveis"):
        horarios = novo_dados["horarios_disponiveis"]
        return resposta_lista_horarios(resposta.texto, horarios)

    return resposta
