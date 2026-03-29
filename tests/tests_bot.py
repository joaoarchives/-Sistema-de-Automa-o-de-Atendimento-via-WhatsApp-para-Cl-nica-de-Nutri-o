"""
Testes unitários — bot.py e agendamento_service.py

Estratégia: mock total de banco e API.
Nenhum teste precisa de MySQL ou WhatsApp rodando.

Executar:
    pytest tests/tests_bot.py -v
"""
from contextlib import contextmanager
from unittest.mock import patch

import pytest

import services.bot as bot
import services.agendamento_service as agendamento_service
from services.agendamento_service import ResultadoAgendamento
from utils.helpers import gerar_horarios

# ─────────────────────────────────────────────────────────────
# Constantes compartilhadas
# ─────────────────────────────────────────────────────────────

TELEFONE = "61999990000"

DADOS_COMPLETOS = {
    "tipo_consulta": "primeira_consulta",
    "periodo": "manha",
    "data": "2099-06-15",
    "horario": "09:00",
    "horarios_disponiveis": ["08:00", "09:00", "10:00"],
    "nome": "Maria Silva",
    "sexo": "feminino",
}


# ─────────────────────────────────────────────────────────────
# Helper de mock para o bot
# ─────────────────────────────────────────────────────────────

@contextmanager
def mock_bot(estado: str, dados: dict | None = None):
    """
    Mocka get_estado, set_estado e registrar_cliente_se_nao_existir.
    Uso:
        with mock_bot("menu") as (get_e, set_e):
            resposta = bot._handle_menu(TELEFONE, "1", {})
    """
    with (
        patch("services.bot.get_estado", return_value=(estado, dados or {})) as get_e,
        patch("services.bot.set_estado") as set_e,
        patch("services.bot.registrar_cliente_se_nao_existir"),
    ):
        yield get_e, set_e


# ─────────────────────────────────────────────────────────────
# processar_mensagem — dispatcher
# ─────────────────────────────────────────────────────────────

class TestProcessarMensagem:

    def test_saudacoes_retornam_menu(self):
        for saudacao in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "menu", "obg"]:
            with mock_bot("menu"):
                resposta = bot.processar_mensagem(TELEFONE, saudacao)
                assert "1 - Agendar consulta" in resposta

    def test_estado_inicio_retorna_menu(self):
        with mock_bot("inicio"):
            resposta = bot.processar_mensagem(TELEFONE, "qualquer coisa")
            assert "1 - Agendar consulta" in resposta

    def test_estado_desconhecido_retorna_menu(self):
        with mock_bot("estado_inexistente"):
            resposta = bot.processar_mensagem(TELEFONE, "1")
            assert "1 - Agendar consulta" in resposta


# ─────────────────────────────────────────────────────────────
# _handle_menu
# ─────────────────────────────────────────────────────────────

class TestHandleMenu:

    def test_opcao_1_vai_para_tipo_consulta(self):
        with mock_bot("menu") as (_, set_e):
            resposta = bot._handle_menu(TELEFONE, "1", {})
            assert "Primeira consulta" in resposta
            set_e.assert_called_once_with(TELEFONE, "tipo_consulta", {})

    def test_opcao_2_cancela_consulta_existente(self):
        with mock_bot("menu"):
            with patch("services.bot.cancelar_consulta", return_value=True):
                resposta = bot._handle_menu(TELEFONE, "2", {})
                assert "cancelada com sucesso" in resposta

    def test_opcao_2_sem_consulta_agendada(self):
        with mock_bot("menu"):
            with patch("services.bot.cancelar_consulta", return_value=False):
                resposta = bot._handle_menu(TELEFONE, "2", {})
                assert "não possui consulta" in resposta

    def test_opcao_invalida(self):
        with mock_bot("menu"):
            resposta = bot._handle_menu(TELEFONE, "9", {})
            assert "Opção inválida" in resposta


# ─────────────────────────────────────────────────────────────
# _handle_tipo_consulta
# ─────────────────────────────────────────────────────────────

class TestHandleTipoConsulta:

    def test_opcao_1_primeira_consulta(self):
        with mock_bot("tipo_consulta") as (_, set_e):
            dados = {}
            bot._handle_tipo_consulta(TELEFONE, "1", dados)
            assert dados["tipo_consulta"] == "primeira_consulta"
            set_e.assert_called_once_with(TELEFONE, "periodo", dados)

    def test_opcao_2_retorno(self):
        with mock_bot("tipo_consulta"):
            dados = {}
            bot._handle_tipo_consulta(TELEFONE, "2", dados)
            assert dados["tipo_consulta"] == "retorno"

    def test_opcao_invalida(self):
        with mock_bot("tipo_consulta"):
            resposta = bot._handle_tipo_consulta(TELEFONE, "5", {})
            assert "Opção inválida" in resposta


# ─────────────────────────────────────────────────────────────
# _handle_periodo
# ─────────────────────────────────────────────────────────────

class TestHandlePeriodo:

    def test_opcao_1_manha(self):
        with mock_bot("periodo") as (_, set_e):
            dados = {}
            bot._handle_periodo(TELEFONE, "1", dados)
            assert dados["periodo"] == "manha"
            set_e.assert_called_once_with(TELEFONE, "data", dados)

    def test_opcao_2_tarde(self):
        with mock_bot("periodo"):
            dados = {}
            bot._handle_periodo(TELEFONE, "2", dados)
            assert dados["periodo"] == "tarde"

    def test_opcao_invalida(self):
        with mock_bot("periodo"):
            resposta = bot._handle_periodo(TELEFONE, "3", {})
            assert "Opção inválida" in resposta


# ─────────────────────────────────────────────────────────────
# _handle_data
# ─────────────────────────────────────────────────────────────

class TestHandleData:

    def test_data_invalida(self):
        with mock_bot("data"):
            resposta = bot._handle_data(TELEFONE, "99/99", {"periodo": "manha"})
            assert "Data inválida" in resposta

    def test_data_valida_sem_horarios(self):
        with mock_bot("data") as (_, set_e):
            with patch("services.bot.buscar_horarios_disponiveis", return_value=[]):
                dados = {"periodo": "manha"}
                resposta = bot._handle_data(TELEFONE, "15/06", dados)
                assert "Não há horários disponíveis" in resposta
                set_e.assert_called_once_with(TELEFONE, "data", dados)

    def test_data_valida_com_horarios(self):
        horarios = ["08:00", "09:00", "10:00"]
        with mock_bot("data") as (_, set_e):
            with patch("services.bot.buscar_horarios_disponiveis", return_value=horarios):
                dados = {"periodo": "manha"}
                resposta = bot._handle_data(TELEFONE, "15/06", dados)
                assert "08:00" in resposta
                assert dados["horarios_disponiveis"] == horarios
                set_e.assert_called_once_with(TELEFONE, "horario", dados)


# ─────────────────────────────────────────────────────────────
# _handle_horario
# ─────────────────────────────────────────────────────────────

class TestHandleHorario:

    def test_entrada_nao_numerica(self):
        with mock_bot("horario"):
            resposta = bot._handle_horario(TELEFONE, "abc", {"horarios_disponiveis": ["08:00"]})
            assert "número correspondente" in resposta

    def test_indice_fora_do_range(self):
        with mock_bot("horario"):
            resposta = bot._handle_horario(TELEFONE, "9", {"horarios_disponiveis": ["08:00"]})
            assert "Horário inválido" in resposta

    def test_selecao_valida(self):
        with mock_bot("horario") as (_, set_e):
            dados = {"horarios_disponiveis": ["08:00", "09:00", "10:00"]}
            resposta = bot._handle_horario(TELEFONE, "2", dados)
            assert dados["horario"] == "09:00"
            assert "nome" in resposta.lower()
            set_e.assert_called_once_with(TELEFONE, "nome", dados)


# ─────────────────────────────────────────────────────────────
# _handle_nome
# ─────────────────────────────────────────────────────────────

class TestHandleNome:

    def test_nome_salvo_em_title_case(self):
        with mock_bot("nome") as (_, set_e):
            dados = {}
            bot._handle_nome(TELEFONE, "maria silva", dados)
            assert dados["nome"] == "Maria Silva"
            set_e.assert_called_once_with(TELEFONE, "sexo", dados)


# ─────────────────────────────────────────────────────────────
# _handle_sexo
# ─────────────────────────────────────────────────────────────

class TestHandleSexo:

    @pytest.mark.parametrize("opcao,esperado", [
        ("1", "masculino"),
        ("2", "feminino"),
        ("3", "outro"),
    ])
    def test_opcoes_validas(self, opcao, esperado):
        with mock_bot("sexo") as (_, set_e):
            dados = {
                "tipo_consulta": "primeira_consulta",
                "data": "2099-06-15",
                "horario": "09:00",
                "nome": "Maria Silva",
            }
            bot._handle_sexo(TELEFONE, opcao, dados)
            assert dados["sexo"] == esperado
            set_e.assert_called_once_with(TELEFONE, "confirmacao", dados)

    def test_opcao_invalida(self):
        with mock_bot("sexo"):
            dados = {
                "tipo_consulta": "retorno",
                "data": "2099-06-15",
                "horario": "09:00",
                "nome": "Maria Silva",
            }
            resposta = bot._handle_sexo(TELEFONE, "9", dados)
            assert "Opção inválida" in resposta


# ─────────────────────────────────────────────────────────────
# _handle_confirmacao
# ─────────────────────────────────────────────────────────────

class TestHandleConfirmacao:

    def test_cancelar_agendamento(self):
        with mock_bot("confirmacao") as (_, set_e):
            resposta = bot._handle_confirmacao(TELEFONE, "2", DADOS_COMPLETOS.copy())
            assert "cancelado" in resposta.lower()
            set_e.assert_called_once_with(TELEFONE, "menu")

    def test_opcao_invalida(self):
        with mock_bot("confirmacao"):
            resposta = bot._handle_confirmacao(TELEFONE, "9", DADOS_COMPLETOS.copy())
            assert "Opção inválida" in resposta

    def test_confirmar_sucesso(self):
        resultado_ok = ResultadoAgendamento(sucesso=True, mensagem="Consulta agendada com sucesso.")
        with mock_bot("confirmacao") as (_, set_e):
            with patch("services.bot.confirmar_agendamento", return_value=resultado_ok):
                resposta = bot._handle_confirmacao(TELEFONE, "1", DADOS_COMPLETOS.copy())
                assert "agendada com sucesso" in resposta
                set_e.assert_called_once_with(TELEFONE, "menu")

    def test_horario_roubado_com_alternativas(self):
        resultado = ResultadoAgendamento(
            sucesso=False,
            mensagem="Esse horário acabou de ser ocupado. Escolha outro horário:",
            horarios_disponiveis=["10:00", "11:00"],
        )
        with mock_bot("confirmacao") as (_, set_e):
            with patch("services.bot.confirmar_agendamento", return_value=resultado):
                dados = DADOS_COMPLETOS.copy()
                resposta = bot._handle_confirmacao(TELEFONE, "1", dados)
                assert "10:00" in resposta
                assert "horario" not in dados
                set_e.assert_called_once_with(TELEFONE, "horario", dados)

    def test_horario_roubado_sem_vagas(self):
        resultado = ResultadoAgendamento(
            sucesso=False,
            mensagem="Não há mais horários disponíveis.\nDigite outra data no formato DD/MM.",
        )
        with mock_bot("confirmacao") as (_, set_e):
            with patch("services.bot.confirmar_agendamento", return_value=resultado):
                dados = DADOS_COMPLETOS.copy()
                bot._handle_confirmacao(TELEFONE, "1", dados)
                set_e.assert_called_once_with(TELEFONE, "data", dados)


# ─────────────────────────────────────────────────────────────
# agendamento_service — buscar_horarios_disponiveis
# ─────────────────────────────────────────────────────────────

class TestBuscarHorariosDisponiveis:

    def test_retorna_apenas_livres(self):
        with patch("services.agendamento_service.buscar_horarios_ocupados", return_value=["08:00", "09:00"]):
            disponiveis = agendamento_service.buscar_horarios_disponiveis("2099-06-15", "manha")
            assert "08:00" not in disponiveis
            assert "09:00" not in disponiveis
            assert len(disponiveis) > 0

    def test_sem_ocupados_retorna_todos(self):
        with patch("services.agendamento_service.buscar_horarios_ocupados", return_value=[]):
            disponiveis = agendamento_service.buscar_horarios_disponiveis("2099-06-15", "manha")
            assert "07:00" in disponiveis
            assert "11:30" in disponiveis

    def test_todos_ocupados_retorna_vazio(self):
        todos = gerar_horarios("manha")
        with patch("services.agendamento_service.buscar_horarios_ocupados", return_value=todos):
            assert agendamento_service.buscar_horarios_disponiveis("2099-06-15", "manha") == []


# ─────────────────────────────────────────────────────────────
# agendamento_service — cancelar_consulta
# ─────────────────────────────────────────────────────────────

class TestCancelarConsulta:

    def test_cancela_com_sucesso(self):
        with patch("services.agendamento_service.cancelar_ultima_consulta", return_value=True):
            assert agendamento_service.cancelar_consulta(TELEFONE) is True

    def test_sem_consulta_retorna_false(self):
        with patch("services.agendamento_service.cancelar_ultima_consulta", return_value=False):
            assert agendamento_service.cancelar_consulta(TELEFONE) is False


# ─────────────────────────────────────────────────────────────
# agendamento_service — confirmar_agendamento
# ─────────────────────────────────────────────────────────────

class TestConfirmarAgendamento:

    def test_horario_livre_salva_e_retorna_sucesso(self):
        with (
            patch("services.agendamento_service.horario_esta_disponivel", return_value=True),
            patch("services.agendamento_service.atualizar_cliente"),
            patch("services.agendamento_service.salvar_consulta"),
            patch("services.agendamento_service.avisar_medico_nova_consulta_hoje"),
        ):
            resultado = agendamento_service.confirmar_agendamento(TELEFONE, DADOS_COMPLETOS.copy())
            assert resultado.sucesso is True
            assert "agendada com sucesso" in resultado.mensagem

    def test_horario_indisponivel_com_alternativas(self):
        with (
            patch("services.agendamento_service.horario_esta_disponivel", return_value=False),
            patch("services.agendamento_service.buscar_horarios_disponiveis", return_value=["10:00", "11:00"]),
        ):
            resultado = agendamento_service.confirmar_agendamento(TELEFONE, DADOS_COMPLETOS.copy())
            assert resultado.sucesso is False
            assert resultado.horarios_disponiveis == ["10:00", "11:00"]
            assert "ocupado" in resultado.mensagem

    def test_horario_indisponivel_sem_vagas(self):
        with (
            patch("services.agendamento_service.horario_esta_disponivel", return_value=False),
            patch("services.agendamento_service.buscar_horarios_disponiveis", return_value=[]),
        ):
            resultado = agendamento_service.confirmar_agendamento(TELEFONE, DADOS_COMPLETOS.copy())
            assert resultado.sucesso is False
            assert resultado.horarios_disponiveis == []

    def test_erro_notificacao_nao_impede_agendamento(self):
        with (
            patch("services.agendamento_service.horario_esta_disponivel", return_value=True),
            patch("services.agendamento_service.atualizar_cliente"),
            patch("services.agendamento_service.salvar_consulta"),
            patch("services.agendamento_service.avisar_medico_nova_consulta_hoje", side_effect=Exception("API fora")),
        ):
            resultado = agendamento_service.confirmar_agendamento(TELEFONE, DADOS_COMPLETOS.copy())
            assert resultado.sucesso is True
