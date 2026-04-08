from unittest.mock import Mock

import pytest

import services.bot as bot
import services.agendamento_service as agendamento_service
from services.agendamento_service import ResultadoAgendamento


TELEFONE = "61999990000"


@pytest.fixture
def dados_agendamento():
    return {
        "plano_codigo": "nutri_trimestral",
        "plano_nome": "Plano Trimestral Premium",
        "plano_adiant": 425.0,
        "tipo_consulta": "primeira_consulta",
        "data": "2099-06-15",
        "horario": "09:00",
        "nome": "Maria Silva",
        "sexo": "feminino",
        "periodo": "manha",
    }


def test_processar_mensagem_inicio_envia_boas_vindas(monkeypatch):
    monkeypatch.setattr(bot, "registrar_cliente_se_nao_existir", lambda telefone: None)
    monkeypatch.setattr(bot, "get_estado", lambda telefone: ("inicio", {}))
    enviar_boas_vindas = Mock(return_value=bot.BotResponse(texto=bot._BOAS_VINDAS))
    monkeypatch.setattr(bot, "_enviar_boas_vindas", enviar_boas_vindas)

    resposta = bot.processar_mensagem(TELEFONE, "oi")

    assert resposta.texto == bot._BOAS_VINDAS
    enviar_boas_vindas.assert_called_once_with(TELEFONE)


def test_processar_mensagem_pedido_localizacao_so_confirma_envio_quando_sucesso(monkeypatch):
    monkeypatch.setattr(bot, "registrar_cliente_se_nao_existir", lambda telefone: None)
    monkeypatch.setattr(bot, "get_estado", lambda telefone: ("boas_vindas", {}))
    send_localizacao = Mock(return_value={"response": {"messages": [{"id": "wamid.localizacao"}]}, "payload": {"type": "text"}})
    registrar = Mock()
    monkeypatch.setattr(bot, "send_localizacao_clinica", send_localizacao)
    monkeypatch.setattr(bot, "_registrar_envio_whatsapp", registrar)

    resposta = bot.processar_mensagem(TELEFONE, "Poderia me enviar a localização do consultório?")

    assert "acabei de te enviar a localizacao" in resposta.texto.lower()
    send_localizacao.assert_called_once_with(TELEFONE)
    registrar.assert_called_once()


def test_processar_mensagem_pedido_localizacao_faz_fallback_honesto_sem_confirmacao(monkeypatch):
    monkeypatch.setattr(bot, "registrar_cliente_se_nao_existir", lambda telefone: None)
    monkeypatch.setattr(bot, "get_estado", lambda telefone: ("boas_vindas", {}))
    send_localizacao = Mock(return_value={"response": {}, "payload": {"type": "text"}})
    registrar = Mock()
    monkeypatch.setattr(bot, "send_localizacao_clinica", send_localizacao)
    monkeypatch.setattr(bot, "_registrar_envio_whatsapp", registrar)

    resposta = bot.processar_mensagem(TELEFONE, "Qual e o endereco do consultorio?")

    assert "nao consegui enviar a localizacao" in resposta.texto.lower()
    assert "rua da contagem" in resposta.texto.lower()
    assert "google.com/maps" in resposta.texto.lower()
    assert "acabei de te enviar" not in resposta.texto.lower()
    send_localizacao.assert_called_once_with(TELEFONE)
    registrar.assert_called_once()


def test_handle_boas_vindas_saudacao_nao_reenvia_fluxo(monkeypatch):
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot._handle_boas_vindas(TELEFONE, "oi", {})

    assert "Posso te ajudar" in resposta.texto
    set_estado.assert_called_once_with(TELEFONE, "boas_vindas", {})


def test_enviar_boas_vindas_retorna_texto_mesmo_sem_pdf(monkeypatch):
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "get_pdf_planos_url", lambda: "")

    resposta = bot._enviar_boas_vindas(TELEFONE)

    assert resposta.texto == bot._BOAS_VINDAS
    set_estado.assert_called_once_with(TELEFONE, "boas_vindas")


def test_processar_mensagem_estado_desconhecido_retorna_menu(monkeypatch):
    monkeypatch.setattr(bot, "registrar_cliente_se_nao_existir", lambda telefone: None)
    monkeypatch.setattr(bot, "get_estado", lambda telefone: ("estado_inexistente", {}))
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot.processar_mensagem(TELEFONE, "qualquer coisa")

    assert resposta.texto == bot._MENU
    set_estado.assert_called_once_with(TELEFONE, "menu")


def test_handle_menu_agendar_retorna_lista_de_planos(monkeypatch):
    planos = [
        {"codigo": "nutri_trimestral", "nome": "Trimestral Premium", "valor_adiantamento": 425},
        {"codigo": "treino_trimestral", "nome": "Trimestral + Treino", "valor_adiantamento": 500},
    ]
    set_estado = Mock()
    monkeypatch.setattr(bot, "buscar_planos_ativos", lambda: planos)
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "detectar_intencao", lambda mensagem: "agendar")

    resposta = bot._handle_menu(TELEFONE, "1", {})

    assert resposta.tipo == "lista"
    assert resposta.lista_botao == "Ver planos"
    assert resposta.lista_secoes[0]["rows"][0]["id"] == "nutri_trimestral"
    set_estado.assert_called_once_with(TELEFONE, "plano", {"planos": ["nutri_trimestral", "treino_trimestral"]})


def test_handle_tipo_consulta_valida_avanca_para_data(monkeypatch):
    dados = {}
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot._handle_tipo_consulta(TELEFONE, "1", dados)

    assert dados["tipo_consulta"] == "primeira_consulta"
    assert "Qual data" in resposta.texto
    set_estado.assert_called_once_with(TELEFONE, "data", dados)


def test_handle_confirmar_data_com_periodo_fixo_vai_para_horario(monkeypatch):
    dados = {
        "tipo_consulta": "primeira_consulta",
        "data_sugerida": "2099-06-15",
        "data_br": "15/06",
        "nome_dia": "segunda-feira",
    }
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "buscar_periodo_do_dia", lambda data: "manha")
    monkeypatch.setattr(bot, "buscar_horarios_disponiveis", lambda data, tipo, periodo: (["09:00", "10:00"], "manha"))

    resposta = bot._handle_confirmar_data(TELEFONE, "sim", dados)

    assert dados["data"] == "2099-06-15"
    assert dados["periodo"] == "manha"
    assert dados["horarios_disponiveis"] == ["09:00", "10:00"]
    assert resposta.texto.startswith("As consultas desse dia")
    set_estado.assert_called_once_with(TELEFONE, "horario", dados)


def test_handle_nome_avanca_para_sexo(monkeypatch):
    dados = {}
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot._handle_nome(TELEFONE, "maria silva", dados)

    assert dados["nome"] == "Maria Silva"
    assert resposta.tipo == "lista"
    assert resposta.lista_botao == "Selecionar"
    set_estado.assert_called_once_with(TELEFONE, "sexo", dados)


def test_handle_sexo_monta_confirmacao(monkeypatch, dados_agendamento):
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot._handle_sexo(TELEFONE, "1", dados_agendamento)

    assert dados_agendamento["sexo"] == "masculino"
    assert resposta.tipo == "lista"
    assert "Confira os dados da sua consulta" in resposta.texto
    set_estado.assert_called_once_with(TELEFONE, "confirmacao", dados_agendamento)


def test_handle_confirmacao_sucesso_envia_pagamento_e_localizacao(monkeypatch, dados_agendamento):
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(
        bot,
        "confirmar_agendamento",
        lambda telefone, dados: ResultadoAgendamento(
            sucesso=True,
            mensagem="Consulta agendada com sucesso.",
            consulta_id=321,
        ),
    )
    send_pagamento = Mock(return_value={"response": {"messages": [{"id": "wamid.1"}]}, "payload": {"type": "text"}})
    send_localizacao = Mock(return_value={"response": {"messages": [{"id": "wamid.2"}]}, "payload": {"type": "text"}})
    registrar = Mock()
    monkeypatch.setattr(bot, "send_pagamento_instrucoes", send_pagamento)
    monkeypatch.setattr(bot, "send_localizacao_clinica", send_localizacao)
    monkeypatch.setattr(bot, "_registrar_envio_whatsapp", registrar)

    resposta = bot._handle_confirmacao(TELEFONE, "1", dados_agendamento)

    assert resposta.texto == ""
    assert dados_agendamento["consulta_id"] == 321
    set_estado.assert_called_once_with(TELEFONE, "aguardando_comprovante", dados_agendamento)
    send_pagamento.assert_called_once_with(TELEFONE, 425.0)
    send_localizacao.assert_called_once_with(TELEFONE)
    assert registrar.call_count == 2


def test_handle_confirmacao_com_alternativas_volta_para_horario(monkeypatch, dados_agendamento):
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(
        bot,
        "confirmar_agendamento",
        lambda telefone, dados: ResultadoAgendamento(
            sucesso=False,
            mensagem="Esse horário acabou de ser ocupado. Escolha outro horário:",
            horarios_disponiveis=["10:00", "10:30"],
            periodo="manha",
        ),
    )

    resposta = bot._handle_confirmacao(TELEFONE, "1", dados_agendamento)

    assert resposta.texto.startswith("Esse horário acabou de ser ocupado")
    assert "horario" not in dados_agendamento
    assert dados_agendamento["horarios_disponiveis"] == ["10:00", "10:30"]
    set_estado.assert_called_once_with(TELEFONE, "horario", dados_agendamento)


def test_processar_comprovante_move_para_analise(monkeypatch):
    set_estado = Mock()
    monkeypatch.setattr(bot, "get_estado", lambda telefone: ("aguardando_comprovante", {"consulta_id": 12}))
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot.processar_comprovante(TELEFONE)

    assert "Comprovante recebido" in resposta.texto
    set_estado.assert_called_once_with(TELEFONE, "pagamento_em_analise", {"consulta_id": 12})


def test_handle_pagamento_em_analise_ok_nao_chama_gemini(monkeypatch):
    set_estado = Mock()
    detectar = Mock(side_effect=AssertionError("nao deveria detectar intencao para ack curto"))
    responder = Mock(side_effect=AssertionError("nao deveria chamar gemini para ack curto"))
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "detectar_intencao", detectar)
    monkeypatch.setattr(bot, "responder_livre", responder)

    resposta = bot._handle_pagamento_em_analise(TELEFONE, "ok", {"consulta_id": 12})

    assert "em análise" in resposta.texto or "em análise" in resposta.texto.lower()
    set_estado.assert_called_once_with(TELEFONE, "pagamento_em_analise", {"consulta_id": 12})


def test_handle_consulta_confirmada_saudacao_nao_reinicia_fluxo(monkeypatch, dados_agendamento):
    set_estado = Mock()
    cancelar = Mock(side_effect=AssertionError("nao deveria cancelar consulta"))
    detectar = Mock(side_effect=AssertionError("nao deveria detectar intencao"))
    responder = Mock(side_effect=AssertionError("nao deveria chamar gemini"))
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "cancelar_consulta", cancelar)
    monkeypatch.setattr(bot, "detectar_intencao", detectar)
    monkeypatch.setattr(bot, "responder_livre", responder)

    resposta = bot._handle_consulta_confirmada(TELEFONE, "boa noite", dados_agendamento)

    assert "consulta segue confirmada" in resposta.texto.lower()
    set_estado.assert_called_once_with(TELEFONE, "consulta_confirmada", dados_agendamento)


def test_handle_consulta_confirmada_agendar_generico_nao_cancela(monkeypatch, dados_agendamento):
    set_estado = Mock()
    cancelar = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)
    monkeypatch.setattr(bot, "cancelar_consulta", cancelar)

    resposta = bot._handle_consulta_confirmada(TELEFONE, "quero outra consulta", dados_agendamento)

    assert "já está confirmada" in resposta.texto.lower()
    cancelar.assert_not_called()
    set_estado.assert_called_once_with(TELEFONE, "consulta_confirmada", dados_agendamento)


def test_handle_consulta_confirmada_fallback_contextual_sem_instabilidade(monkeypatch, dados_agendamento):
    monkeypatch.setattr(
        bot,
        "responder_livre",
        lambda mensagem: "Desculpe, estou com uma instabilidade no momento. Para agendar uma consulta, digite 1. Para cancelar, digite 2.",
    )
    set_estado = Mock()
    monkeypatch.setattr(bot, "set_estado", set_estado)

    resposta = bot._handle_consulta_confirmada(TELEFONE, "tenho uma dúvida rápida", dados_agendamento)

    assert "instabilidade" not in resposta.texto.lower()
    assert "consulta segue confirmada" in resposta.texto.lower()


def test_processar_mensagem_converte_horarios_em_lista(monkeypatch):
    estados = [("data", {"tipo_consulta": "primeira_consulta"}), ("horario", {"horarios_disponiveis": ["09:00", "09:30"]})]
    monkeypatch.setattr(bot, "registrar_cliente_se_nao_existir", lambda telefone: None)
    monkeypatch.setattr(bot, "get_estado", lambda telefone: estados.pop(0))
    monkeypatch.setitem(bot._HANDLERS, "data", lambda telefone, mensagem, dados: bot.BotResponse(texto="Selecione um horário:"))

    resposta = bot.processar_mensagem(TELEFONE, "15/06")

    assert resposta.tipo == "lista"
    assert resposta.lista_botao == "Ver horários"
    assert resposta.lista_secoes[0]["rows"][0]["id"] == "09:00"


def test_busca_horarios_disponiveis_retorna_tupla(monkeypatch):
    monkeypatch.setattr(agendamento_service, "buscar_periodo_do_dia", lambda data: None)
    monkeypatch.setattr(agendamento_service, "buscar_horarios_ocupados", lambda data: ["09:00"])

    livres, periodo = agendamento_service.buscar_horarios_disponiveis("2099-06-15", "primeira_consulta", "manha")

    assert periodo == "manha"
    assert "09:00" not in livres
    assert "10:00" in livres


def test_confirmar_agendamento_sucesso(monkeypatch, dados_agendamento):
    monkeypatch.setattr(agendamento_service, "buscar_plano_por_codigo", lambda codigo: {"id": 7})
    monkeypatch.setattr(agendamento_service, "horario_esta_disponivel", lambda data, horario: True)
    atualizar_cliente = Mock()
    salvar_consulta = Mock(return_value=123)
    avisar_medico = Mock()
    monkeypatch.setattr(agendamento_service, "atualizar_cliente", atualizar_cliente)
    monkeypatch.setattr(agendamento_service, "salvar_consulta", salvar_consulta)
    monkeypatch.setattr(agendamento_service, "avisar_medico_nova_consulta_hoje", avisar_medico)

    resultado = agendamento_service.confirmar_agendamento(TELEFONE, dados_agendamento)

    assert resultado.sucesso is True
    assert resultado.consulta_id == 123
    atualizar_cliente.assert_called_once_with(TELEFONE, "Maria Silva", "feminino")
    salvar_consulta.assert_called_once()
    avisar_medico.assert_called_once_with(TELEFONE, "2099-06-15", "09:00")


def test_confirmar_agendamento_indisponivel_com_alternativas(monkeypatch, dados_agendamento):
    monkeypatch.setattr(agendamento_service, "buscar_plano_por_codigo", lambda codigo: {"id": 7})
    monkeypatch.setattr(agendamento_service, "horario_esta_disponivel", lambda data, horario: False)
    monkeypatch.setattr(
        agendamento_service,
        "buscar_horarios_disponiveis",
        lambda data, tipo, periodo: (["10:00", "10:30"], "manha"),
    )

    resultado = agendamento_service.confirmar_agendamento(TELEFONE, dados_agendamento)

    assert resultado.sucesso is False
    assert resultado.periodo == "manha"
    assert resultado.horarios_disponiveis == ["10:00", "10:30"]


def test_confirmar_agendamento_indisponivel_sem_vagas(monkeypatch, dados_agendamento):
    monkeypatch.setattr(agendamento_service, "buscar_plano_por_codigo", lambda codigo: {"id": 7})
    monkeypatch.setattr(agendamento_service, "horario_esta_disponivel", lambda data, horario: False)
    monkeypatch.setattr(agendamento_service, "buscar_horarios_disponiveis", lambda data, tipo, periodo: ([], "manha"))

    resultado = agendamento_service.confirmar_agendamento(TELEFONE, dados_agendamento)

    assert resultado.sucesso is False
    assert resultado.horarios_disponiveis == []
    assert "Digite outra data" in resultado.mensagem


def test_confirmar_agendamento_detecta_corrida_apos_precheck(monkeypatch, dados_agendamento):
    monkeypatch.setattr(agendamento_service, "buscar_plano_por_codigo", lambda codigo: {"id": 7})
    monkeypatch.setattr(agendamento_service, "horario_esta_disponivel", lambda data, horario: True)
    monkeypatch.setattr(agendamento_service, "atualizar_cliente", lambda *args, **kwargs: None)
    monkeypatch.setattr(agendamento_service, "salvar_consulta", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        agendamento_service,
        "buscar_horarios_disponiveis",
        lambda data, tipo, periodo: (["10:00", "10:30"], "manha"),
    )
    avisar_medico = Mock()
    monkeypatch.setattr(agendamento_service, "avisar_medico_nova_consulta_hoje", avisar_medico)

    resultado = agendamento_service.confirmar_agendamento(TELEFONE, dados_agendamento)

    assert resultado.sucesso is False
    assert resultado.horarios_disponiveis == ["10:00", "10:30"]
    assert "ocupado" in resultado.mensagem.lower()
    avisar_medico.assert_not_called()
