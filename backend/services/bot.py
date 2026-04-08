"""
Fluxo de conversa do bot.

Estados:
  inicio → boas_vindas → menu → plano → tipo_consulta → data → confirmar_data
  → periodo_livre → horario → nome → sexo → confirmacao
  → aguardando_comprovante → pagamento_em_analise → consulta_confirmada

Regras de negócio  → agendamento_service.py
Persistência       → database/estados.py
IA                 → services/gemini.py
"""
from datetime import datetime

from services.bot_response import BotResponse
from database.mensagens import salvar_log_whatsapp
from database.clientes import registrar_cliente_se_nao_existir
from database.consultas import buscar_periodo_do_dia, buscar_planos_ativos
from database.estados import get_estado, set_estado
from services.agendamento_service import (
    ResultadoAgendamento,
    buscar_horarios_disponiveis,
    cancelar_consulta,
    confirmar_agendamento,
)
from services.gemini import detectar_intencao, interpretar_data, responder_livre
from services.whatsapp import (
    get_pdf_planos_url,
    send_localizacao_clinica,
    send_pagamento_instrucoes,
    send_whatsapp_document,
    send_whatsapp_message,
)
from utils.helpers import data_valida, formatar_data_br, formatar_data_iso
from utils.time_utils import local_today

import logging
logger = logging.getLogger(__name__)

_SAUDACOES = {"oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"}

_MENU = (
    "Olá! Seja bem-vindo ao consultório do nutricionista Paulo Jordão. 💪\n\n"
    "Sou a Sofia, sua assistente virtual. Como posso te ajudar?\n\n"
    "1 - Agendar consulta\n"
    "2 - Cancelar consulta\n\n"
    "Ou me faça qualquer pergunta sobre os planos, serviços e nutrição!"
)

_BOAS_VINDAS = (
    "Olá! Seja bem-vindo ao consultório do nutricionista Paulo Jordão. 💪\n\n"
    "Sou a Sofia, sua assistente virtual!\n\n"
    "Acabei de te enviar nossa tabela de planos. 📋\n\n"
    "Você gostaria de agendar uma consulta ou tem alguma dúvida sobre os planos e serviços?"
)

_DIAS_PT = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira",
    3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo",
}

_SIM = {"sim", "s", "yes", "1", "ok", "isso", "correto", "certo", "exato", "confirmado"}
_NAO = {"não", "nao", "n", "no", "2", "errado", "incorreto", "outro", "outra", "negativo"}

_AGRADECIMENTOS = {
    "obrigado", "obrigada", "obg", "valeu", "vlw", "muito obrigado", "muito obrigada",
    "ta bom", "tá bom", "ta ótimo", "tá ótimo", "ok obrigado", "ok obrigada",
    "perfeito obrigado", "ótimo obrigado", "show", "show de bola",
    "entendido", "certo obrigado", "beleza", "👍", "🙏",
}

_PERIODO_LABEL = {
    "manha": "manhã (09:00 às 12:00)",
    "tarde": "tarde (16:00 às 19:00)",
}


def _registrar_envio_whatsapp(telefone: str, resultado: dict, tipo_mensagem: str | None = None) -> None:
    response_data = resultado.get("response", {}) if isinstance(resultado, dict) else {}
    payload = resultado.get("payload", {}) if isinstance(resultado, dict) else {}
    payload_type = payload.get("type")
    tipo = tipo_mensagem or payload_type or "texto"

    if tipo == "text":
        tipo = "texto"
    elif tipo == "interactive":
        tipo = "lista"

    salvar_log_whatsapp(
        telefone_destino=telefone,
        tipo_mensagem=tipo,
        message_id=response_data.get("messages", [{}])[0].get("id"),
        status_envio="erro" if not response_data.get("messages") else "enviado",
        payload=payload,
        resposta_api=response_data,
    )


def _enviar_boas_vindas(telefone: str) -> BotResponse:
    set_estado(telefone, "boas_vindas")
    pdf_planos_url = get_pdf_planos_url()
    if not pdf_planos_url:
        logger.warning("PDF dos planos indisponível para boas-vindas - telefone=%s", telefone)
        return BotResponse(texto=_BOAS_VINDAS)

    try:
        resultado = send_whatsapp_document(
            telefone,
            pdf_planos_url,
            "Planos_2026.pdf",
            "Confira nossos planos 👆",
        )
        _registrar_envio_whatsapp(telefone, resultado, "document")
    except Exception:
        logger.exception("Erro ao enviar PDF dos planos")

    return BotResponse(texto=_BOAS_VINDAS)


def _nome_dia(data_iso: str) -> str:
    try:
        dt = datetime.strptime(data_iso, "%Y-%m-%d")
        return _DIAS_PT[dt.weekday()]
    except ValueError:
        return "data informada"


def _hoje_str() -> str:
    return local_today().strftime("%d/%m/%Y")


def _hoje_nome() -> str:
    return _DIAS_PT[local_today().weekday()]


def _handle_boas_vindas(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem in _SAUDACOES:
        return _enviar_boas_vindas(telefone)

    if mensagem in _AGRADECIMENTOS:
        set_estado(telefone, "boas_vindas", dados)
        return BotResponse(texto=(
            "De nada! 😊 Estou por aqui se precisar de mais alguma coisa.\n\n"
            "Posso te ajudar com alguma dúvida ou gostaria de agendar uma consulta?"
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

    resposta_gemini = responder_livre(mensagem)
    set_estado(telefone, "boas_vindas", dados)
    return BotResponse(texto=(
        f"{resposta_gemini}\n\n"
        "Posso te ajudar com mais alguma dúvida ou gostaria de agendar uma consulta? 😊"
    ))


def _handle_menu(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    msg = mensagem.strip().lower()
    if msg in {"1", "agendar", "marcar"} or detectar_intencao(msg) == "agendar":
        planos = buscar_planos_ativos()
        set_estado(telefone, "plano", {"planos": [p["codigo"] for p in planos]})

        nomes_curtos = {
            "nutri_consulta_unica": "Consulta Completa",
            "nutri_trimestral": "Trimestral Premium",
            "nutri_semestral": "Semestral Alta Perf.",
            "nutri_grupo_1amigo": "Grupo — 1 amigo",
            "nutri_grupo_2amigos": "Grupo — 2 amigos",
            "treino_consulta_unica": "Consulta + Treino",
            "treino_trimestral": "Trimestral + Treino",
            "treino_semestral": "Semestral + Treino",
            "treino_grupo_1amigo": "Grupo+Treino 1 amigo",
            "treino_grupo_2amigos": "Grupo+Treino 2 amigos",
        }

        nutri = [p for p in planos if not p["codigo"].startswith("treino")]
        treino = [p for p in planos if p["codigo"].startswith("treino")]

        secoes = []
        if nutri:
            secoes.append({
                "title": "Só Nutrição",
                "rows": [{"id": p["codigo"], "title": nomes_curtos.get(p["codigo"], p["nome"][:24])} for p in nutri],
            })
        if treino:
            secoes.append({
                "title": "Nutrição + Treino",
                "rows": [{"id": p["codigo"], "title": nomes_curtos.get(p["codigo"], p["nome"][:24])} for p in treino],
            })

        return BotResponse(
            texto="Qual plano você tem interesse? 📋",
            tipo="lista",
            lista_botao="Ver planos",
            lista_secoes=secoes,
        )

    if msg == "2" or "cancel" in msg:
        cancelada = cancelar_consulta(telefone)
        set_estado(telefone, "menu")
        return BotResponse(texto=(
            "Sua consulta foi cancelada com sucesso. ✅"
            if cancelada
            else "Você não possui consulta agendada para cancelar."
        ))

    return BotResponse(texto=responder_livre(mensagem))


def _handle_plano(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    planos = buscar_planos_ativos()

    plano_escolhido = None
    for plano in planos:
        if mensagem == plano["codigo"]:
            plano_escolhido = plano
            break

    if not plano_escolhido and mensagem.isdigit():
        idx = int(mensagem) - 1
        if 0 <= idx < len(planos):
            plano_escolhido = planos[idx]

    if not plano_escolhido:
        return BotResponse(texto="Opção inválida. Por favor, selecione um plano da lista.")

    dados["plano_codigo"] = plano_escolhido["codigo"]
    dados["plano_nome"] = plano_escolhido["nome"]
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
        return BotResponse(
            texto="Por favor, selecione o tipo da consulta: 🩺",
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

    dados["tipo_consulta"] = tipos[mensagem]
    set_estado(telefone, "data", dados)
    return BotResponse(texto=(
        "Qual data você gostaria? 📅 Pode escrever normalmente, "
        "como \"sexta-feira\", \"amanhã\" ou no formato DD/MM."
    ))


def _handle_data(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if data_valida(mensagem):
        data_iso = formatar_data_iso(mensagem)
        data_br = mensagem[:5]
        nome_dia = _nome_dia(data_iso)
        dados.update({"data_sugerida": data_iso, "data_br": data_br, "nome_dia": nome_dia})
        set_estado(telefone, "confirmar_data", dados)
        return BotResponse(texto=f"{nome_dia.capitalize()}, dia {data_br}? Está correto? Responda sim ou não. 📅")

    resultado = interpretar_data(mensagem, _hoje_str(), _hoje_nome())
    if not resultado.get("sucesso"):
        return BotResponse(texto="Não consegui entender a data. Pode escrever no formato DD/MM? Exemplo: 15/04.")

    data_br = resultado["data"][:5]
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
    if mensagem in _NAO:
        dados.pop("data_sugerida", None)
        dados.pop("data_br", None)
        dados.pop("nome_dia", None)
        set_estado(telefone, "data", dados)
        return BotResponse(texto="Tudo bem! Digite a data desejada no formato DD/MM ou escreva normalmente. 📅")

    if mensagem not in _SIM:
        return BotResponse(texto=(
            f"{dados['nome_dia'].capitalize()}, dia {dados['data_br']}? Responda sim ou não."
        ))

    dados["data"] = dados.pop("data_sugerida")
    dados.pop("data_br", None)
    dados.pop("nome_dia", None)

    tipo_consulta = dados["tipo_consulta"]
    periodo_ativo = buscar_periodo_do_dia(dados["data"])

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
        return BotResponse(texto=f"As consultas desse dia são no período da {label}. Selecione um horário: ⏰")

    set_estado(telefone, "periodo_livre", dados)
    return BotResponse(
        texto="Qual período você prefere? ☀️🌙",
        tipo="lista",
        lista_botao="Selecionar período",
        lista_secoes=[{
            "title": "Período disponível",
            "rows": [
                {"id": "1", "title": "Manhã (09:00 às 12:00)"},
                {"id": "2", "title": "Tarde (16:00 às 19:00)"},
            ],
        }],
    )


def _handle_periodo_livre(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    periodos = {"1": "manha", "2": "tarde"}
    if mensagem not in periodos:
        return BotResponse(
            texto="Por favor, selecione um período: ☀️🌙",
            tipo="lista",
            lista_botao="Selecionar período",
            lista_secoes=[{
                "title": "Período disponível",
                "rows": [
                    {"id": "1", "title": "Manhã (09:00 às 12:00)"},
                    {"id": "2", "title": "Tarde (16:00 às 19:00)"},
                ],
            }],
        )

    dados["periodo"] = periodos[mensagem]
    disponiveis, _ = buscar_horarios_disponiveis(dados["data"], dados["tipo_consulta"], dados["periodo"])

    if not disponiveis:
        set_estado(telefone, "data", dados)
        return BotResponse(texto="Não há horários disponíveis para essa data nesse período.\nDigite outra data no formato DD/MM.")

    dados["horarios_disponiveis"] = disponiveis
    set_estado(telefone, "horario", dados)
    return BotResponse(texto="Ótimo! Selecione um horário disponível: ⏰")


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

    return BotResponse(
        texto="Qual o seu sexo? 👤",
        tipo="lista",
        lista_botao="Selecionar",
        lista_secoes=[{
            "title": "Sexo",
            "rows": [
                {"id": "1", "title": "Masculino"},
                {"id": "2", "title": "Feminino"},
                {"id": "3", "title": "Outro"},
            ],
        }],
    )


def _handle_sexo(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    opcoes = {"1": "masculino", "2": "feminino", "3": "outro"}
    if mensagem not in opcoes:
        return BotResponse(
            texto="Por favor, selecione seu sexo: 👤",
            tipo="lista",
            lista_botao="Selecionar",
            lista_secoes=[{
                "title": "Sexo",
                "rows": [
                    {"id": "1", "title": "Masculino"},
                    {"id": "2", "title": "Feminino"},
                    {"id": "3", "title": "Outro"},
                ],
            }],
        )

    dados["sexo"] = opcoes[mensagem]
    tipo_fmt = "Primeira Consulta" if dados["tipo_consulta"] == "primeira_consulta" else "Retorno"

    set_estado(telefone, "confirmacao", dados)
    return BotResponse(
        texto=(
            f"Confira os dados da sua consulta: 📋\n\n"
            f"Plano: {dados.get('plano_nome', '-')}\n"
            f"Tipo: {tipo_fmt}\n"
            f"Nome: {dados['nome']}\n"
            f"Sexo: {dados['sexo']}\n"
            f"Data: {formatar_data_br(dados['data'])}\n"
            f"Horário: {dados['horario']}\n\n"
            f"Tudo certo?"
        ),
        tipo="lista",
        lista_botao="Confirmar",
        lista_secoes=[{
            "title": "Confirmação",
            "rows": [
                {"id": "1", "title": "✅ Confirmar agendamento"},
                {"id": "2", "title": "❌ Cancelar"},
            ],
        }],
    )


def _handle_confirmacao(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem == "2":
        set_estado(telefone, "boas_vindas")
        return BotResponse(texto=(
            "Agendamento cancelado.\n\n"
            "Se quiser, posso te ajudar com outra data ou tirar alguma dúvida. 😊"
        ))

    if mensagem != "1":
        return BotResponse(
            texto="Por favor, confirme ou cancele o agendamento:",
            tipo="lista",
            lista_botao="Confirmar",
            lista_secoes=[{
                "title": "Confirmação",
                "rows": [
                    {"id": "1", "title": "✅ Confirmar agendamento"},
                    {"id": "2", "title": "❌ Cancelar"},
                ],
            }],
        )

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
        resultado_pagamento = send_pagamento_instrucoes(telefone, valor_adiant)
        _registrar_envio_whatsapp(telefone, resultado_pagamento, "texto")

        resultado_localizacao = send_localizacao_clinica(telefone)
        _registrar_envio_whatsapp(telefone, resultado_localizacao, "texto")
    except Exception:
        logger.exception("Erro ao enviar instruções finais do agendamento - telefone=%s", telefone)

    return BotResponse(texto="")


def _handle_aguardando_comprovante(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem in _AGRADECIMENTOS:
        return BotResponse(texto="De nada! 😊 Assim que o Dr. Paulo confirmar o pagamento, você receberá uma mensagem.")

    return BotResponse(texto=(
        "Estamos aguardando o comprovante de pagamento. 📎\n\n"
        "Por favor, envie a imagem do comprovante aqui nesta conversa."
    ))


def _handle_pagamento_em_analise(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    intencao = detectar_intencao(mensagem)

    if intencao == "recusar":
        return BotResponse(texto=(
            "De nada! 😊 Fico feliz em poder ajudar.\n\n"
            "Assim que o Dr. Paulo confirmar o pagamento, você receberá uma mensagem. "
            "Até logo! 💪"
        ))

    if intencao == "agendar":
        return BotResponse(texto=(
            "Seu comprovante está em análise. 🙏\n\n"
            "Assim que o pagamento for confirmado, ficará tudo certo! "
            "Caso queira agendar outra consulta, é só nos contatar depois."
        ))

    resposta_gemini = responder_livre(mensagem)
    set_estado(telefone, "pagamento_em_analise", dados)
    return BotResponse(texto=(
        f"{resposta_gemini}\n\n"
        "Lembrando que seu comprovante está em análise. "
        "Assim que o Dr. Paulo confirmar, você receberá uma mensagem. 🙏"
    ))


_REAGENDAR = {
    "reagendar", "remarcar", "alterar data", "mudar data", "alterar horario",
    "mudar horario", "alterar a data", "mudar a data", "alterar o horario",
    "trocar data", "trocar horario", "quero alterar", "quero mudar",
    "quero reagendar", "quero remarcar",
}


def _handle_consulta_confirmada(telefone: str, mensagem: str, dados: dict) -> BotResponse:
    if mensagem in _AGRADECIMENTOS:
        set_estado(telefone, "consulta_confirmada", dados)
        return BotResponse(texto="De nada! 😊 Até o dia da consulta! 💪")

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
        return BotResponse(texto="Até logo! Se precisar de algo, é só chamar. 😊")

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


def processar_comprovante(telefone: str) -> BotResponse:
    _, dados = get_estado(telefone)
    set_estado(telefone, "pagamento_em_analise", dados)
    return BotResponse(texto=(
        "Comprovante recebido! ✅\n\n"
        "Aguardando a confirmação do pagamento pelo Dr. Paulo. "
        "Em breve você receberá a confirmação. 🙏"
    ))


def processar_mensagem(telefone: str, mensagem: str) -> BotResponse:
    registrar_cliente_se_nao_existir(telefone)
    mensagem_original = (mensagem or "").strip()
    mensagem = mensagem_original.lower()
    estado, dados = get_estado(telefone)

    if estado == "inicio":
        return _enviar_boas_vindas(telefone)

    if mensagem == "menu":
        set_estado(telefone, "menu")
        return BotResponse(texto=_MENU)

    handler = _HANDLERS.get(estado)
    if handler is None:
        set_estado(telefone, "menu")
        return BotResponse(texto=_MENU)

    mensagem_handler = mensagem_original if estado == "nome" else mensagem
    resposta = handler(telefone, mensagem_handler, dados)

    novo_estado, novo_dados = get_estado(telefone)
    if novo_estado == "horario" and novo_dados.get("horarios_disponiveis"):
        horarios = novo_dados["horarios_disponiveis"]
        return BotResponse(
            texto=resposta.texto,
            tipo="lista",
            lista_botao="Ver horários",
            lista_secoes=[{
                "title": "Horários disponíveis",
                "rows": [{"id": horario, "title": horario} for horario in horarios],
            }],
        )

    return resposta
