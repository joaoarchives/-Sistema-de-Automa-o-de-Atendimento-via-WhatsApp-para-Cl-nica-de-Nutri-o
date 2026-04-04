from services.bot_response import BotResponse


PLANOS_NOMES_CURTOS = {
    "nutri_consulta_unica": "Consulta Completa",
    "nutri_trimestral": "Trimestral Premium",
    "nutri_semestral": "Semestral Alta Perf.",
    "nutri_grupo_1amigo": "Grupo - 1 amigo",
    "nutri_grupo_2amigos": "Grupo - 2 amigos",
    "treino_consulta_unica": "Consulta + Treino",
    "treino_trimestral": "Trimestral + Treino",
    "treino_semestral": "Semestral + Treino",
    "treino_grupo_1amigo": "Grupo+Treino 1 amigo",
    "treino_grupo_2amigos": "Grupo+Treino 2 amigos",
}


def resposta_lista_planos(planos: list[dict]) -> BotResponse:
    nutri = [p for p in planos if not p["codigo"].startswith("treino")]
    treino = [p for p in planos if p["codigo"].startswith("treino")]
    secoes = []

    if nutri:
        secoes.append(
            {
                "title": "So Nutricao",
                "rows": [
                    {
                        "id": p["codigo"],
                        "title": PLANOS_NOMES_CURTOS.get(p["codigo"], p["nome"][:24]),
                    }
                    for p in nutri
                ],
            }
        )

    if treino:
        secoes.append(
            {
                "title": "Nutricao + Treino",
                "rows": [
                    {
                        "id": p["codigo"],
                        "title": PLANOS_NOMES_CURTOS.get(p["codigo"], p["nome"][:24]),
                    }
                    for p in treino
                ],
            }
        )

    return BotResponse(
        texto="Qual plano voce tem interesse? 📋",
        tipo="lista",
        lista_botao="Ver planos",
        lista_secoes=secoes,
    )


def resposta_lista_tipo_consulta(texto: str) -> BotResponse:
    return BotResponse(
        texto=texto,
        tipo="lista",
        lista_botao="Selecionar tipo",
        lista_secoes=[
            {
                "title": "Tipo de consulta",
                "rows": [
                    {"id": "1", "title": "Primeira consulta"},
                    {"id": "2", "title": "Retorno"},
                ],
            }
        ],
    )


def resposta_lista_periodo(texto: str) -> BotResponse:
    return BotResponse(
        texto=texto,
        tipo="lista",
        lista_botao="Selecionar periodo",
        lista_secoes=[
            {
                "title": "Periodo disponivel",
                "rows": [
                    {"id": "1", "title": "Manha (09:00 as 12:00)"},
                    {"id": "2", "title": "Tarde (16:00 as 19:00)"},
                ],
            }
        ],
    )


def resposta_lista_sexo(texto: str) -> BotResponse:
    return BotResponse(
        texto=texto,
        tipo="lista",
        lista_botao="Selecionar",
        lista_secoes=[
            {
                "title": "Sexo",
                "rows": [
                    {"id": "1", "title": "Masculino"},
                    {"id": "2", "title": "Feminino"},
                    {"id": "3", "title": "Outro"},
                ],
            }
        ],
    )


def resposta_lista_confirmacao(texto: str) -> BotResponse:
    return BotResponse(
        texto=texto,
        tipo="lista",
        lista_botao="Confirmar",
        lista_secoes=[
            {
                "title": "Confirmacao",
                "rows": [
                    {"id": "1", "title": "Confirmar agendamento"},
                    {"id": "2", "title": "Cancelar"},
                ],
            }
        ],
    )


def resposta_lista_horarios(texto: str, horarios: list[str]) -> BotResponse:
    return BotResponse(
        texto=texto,
        tipo="lista",
        lista_botao="Ver horarios",
        lista_secoes=[
            {
                "title": "Horarios disponiveis",
                "rows": [{"id": horario, "title": horario} for horario in horarios],
            }
        ],
    )
