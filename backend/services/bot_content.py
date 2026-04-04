from datetime import date


SAUDACOES = {"menu", "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "obg"}

MENU = (
    "Olá! Seja bem-vindo ao consultório do nutricionista Paulo Jordão. 💪\n\n"
    "Sou a Sofia, sua assistente virtual. Como posso te ajudar?\n\n"
    "1 - Agendar consulta\n"
    "2 - Cancelar consulta\n\n"
    "Ou me faça qualquer pergunta sobre os planos, serviços e nutrição!"
)

BOAS_VINDAS = (
    "Olá! Seja bem-vindo ao consultório do nutricionista Paulo Jordão. 💪\n\n"
    "Sou a Sofia, sua assistente virtual!\n\n"
    "Acabei de te enviar nossa tabela de planos. 📋\n\n"
    "Você gostaria de agendar uma consulta ou tem alguma dúvida sobre os planos e serviços?"
)

DIAS_PT = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

SIM = {"sim", "s", "yes", "1", "ok", "isso", "correto", "certo", "exato", "confirmado"}
NAO = {"não", "nao", "n", "no", "2", "errado", "incorreto", "outro", "outra", "negativo"}

AGRADECIMENTOS = {
    "obrigado", "obrigada", "obg", "valeu", "vlw", "muito obrigado", "muito obrigada",
    "ta bom", "tá bom", "ta ótimo", "tá ótimo", "ok obrigado", "ok obrigada",
    "perfeito obrigado", "ótimo obrigado", "show", "show de bola",
    "entendido", "certo obrigado", "beleza", "👍", "🙏",
}

PERIODO_LABEL = {
    "manha": "manhã (09:00 às 12:00)",
    "tarde": "tarde (16:00 às 19:00)",
}

PALAVRAS_CONFIRMACAO = {
    "confirmado", "confirmada", "confirmar", "confirmou",
    "aprovado", "aprovada", "aprovou", "liberado", "liberada",
}

PALAVRAS_COMPROVANTE = {
    "comprovante", "pix", "pagamento", "pagou", "paguei",
    "transferencia", "transferência",
}

PRE_CONSULTA = (
    "Recomendações pré-consulta do Dr. Paulo:\n\n"
    "Use roupas adequadas para avaliação física.\n"
    "Homens: sunga ou calção.\n"
    "Mulheres: biquíni ou short e top.\n\n"
    "Aguardando a confirmação do pagamento pelo Dr. Paulo. "
    "Em breve você receberá a confirmação. 🙏"
)

PALAVRAS_LOCALIZACAO = {
    "endereco", "endereço", "localizacao", "localização",
    "localizacao da clinica", "localização da clínica",
    "onde fica", "onde e", "onde é", "como chegar", "mapa",
    "endereco da clinica", "endereço da clínica", "clinica fica",
}

MAPS_CLINICA = (
    "https://www.google.com/maps/search/"
    "Rua+da+Contagem,+1985,+Paracatu+MG,+38603-400,+Brasil"
)

LOCALIZACAO_CLINICA = (
    "A clínica fica na Rua da Contagem, 1985, Paracatu - MG, CEP 38603-400.\n"
    "1º andar, sala 113.\n\n"
    f"Localização no mapa: {MAPS_CLINICA}"
)


def encerramento_menu() -> str:
    return "Se quiser, também posso tirar outra dúvida ou te ajudar a agendar uma consulta. 😊"


def encerramento_suave() -> str:
    return "Se quiser, posso continuar te ajudando por aqui. 😊"


def mensagem_tem_localizacao(mensagem: str) -> bool:
    msg = (mensagem or "").strip().lower()
    return any(p in msg for p in PALAVRAS_LOCALIZACAO)


def resposta_localizacao(incluir_encerramento: bool = True) -> str:
    texto = LOCALIZACAO_CLINICA
    if incluir_encerramento:
        texto += "\n\nSe quiser, também posso te ajudar com mais alguma dúvida."
    return texto


def hoje_str() -> str:
    return date.today().strftime("%d/%m/%Y")


def hoje_nome() -> str:
    return DIAS_PT[date.today().weekday()]
