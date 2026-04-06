"""
Serviço de integração com o Google Gemini (google-genai SDK).

Responsabilidades:
- Responder mensagens livres fora do fluxo de agendamento
- Interpretar datas e horários escritos em linguagem natural
- Responder dúvidas sobre nutrição e a clínica
"""
import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client = None


# ── Fallback local para datas sem chamar a API ───────────────────────────────

from datetime import date, timedelta

_DIAS_SEMANA_PT = {
    "segunda": 0, "segunda-feira": 0, "segunda feira": 0,
    "terça": 1, "terca": 1, "terça-feira": 1, "terca-feira": 1, "terça feira": 1, "terca feira": 1,
    "quarta": 2, "quarta-feira": 2, "quarta feira": 2,
    "quinta": 3, "quinta-feira": 3, "quinta feira": 3,
    "sexta": 4, "sexta-feira": 4, "sexta feira": 4,
    "sábado": 5, "sabado": 5,
    "domingo": 6,
}

def _fallback_data_local(mensagem: str) -> dict | None:
    """Tenta interpretar datas comuns sem chamar a API."""
    msg = mensagem.strip().lower()

    # Hoje / amanhã
    if msg in ("hoje",):
        return {"data": date.today().strftime("%d/%m/%Y"), "sucesso": True}
    if msg in ("amanhã", "amanha"):
        d = date.today() + timedelta(days=1)
        return {"data": d.strftime("%d/%m/%Y"), "sucesso": True}

    # Dia da semana → próxima ocorrência a partir de amanhã
    for nome, weekday in _DIAS_SEMANA_PT.items():
        if msg == nome or msg.startswith(nome):
            hoje = date.today()
            dias_ate = (weekday - hoje.weekday()) % 7
            if dias_ate == 0:
                dias_ate = 7  # se hoje é o mesmo dia, vai para a próxima semana
            d = hoje + timedelta(days=dias_ate)
            return {"data": d.strftime("%d/%m/%Y"), "sucesso": True}

    return None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


SYSTEM_PROMPT = """
Você é a Sofia, secretária virtual do nutricionista Paulo Jordão.
Atende pacientes via WhatsApp de forma simpática, acolhedora e profissional.
Escreva sempre em português brasileiro informal mas profissional.

SOBRE O PAULO JORDÃO:
- Nutricionista especializado em Alta Performance e Estética
- CRN-9: 29001
- Graduado pela Universidade Atenas
- Pós-graduado em Bodybuilding Coach e Hormonização (Uniguaçu)
- Treinador pela CBMF
- Mais de 4 anos de atuação e mais de 600 pacientes atendidos
- Instagram: @paulosjn_nutri

SERVIÇOS OFERECIDOS:
- Avaliação física completa (peso, estatura, circunferências, dobras cutâneas, % de gordura, massa magra)
- Planejamento de dieta individualizada
- Dieta flexível com contagem de macros
- Suplementação e manipulados (quando necessário)
- Treino personalizado e periodizado
- Acompanhamento online via aplicativo Web Diet (60 dias até 6 meses conforme o plano)

PLANOS — SÓ NUTRIÇÃO:
1. Consulta Nutricional Completa — R$ 450,00
   Avaliação inicial + plano alimentar personalizado + retorno após 30 dias

2. Pacote Trimestral Premium — R$ 850,00 (o mais popular)
   3 meses de acompanhamento, 3 retornos (intervalo de 30 dias), plano alimentar com ajustes, suporte prioritário

3. Plano Semestral Alta Performance — R$ 1.600,00
   6 meses, 6 retornos (intervalo de 30 dias), suporte premium

4. Consulta em grupo (desconto com amigos):
   Com 1 amigo: R$ 400,00 por pessoa
   Com 2 amigos: R$ 360,00 por pessoa
   Obs.: todas as consultas do grupo devem ser no mesmo dia

PLANOS — NUTRIÇÃO + TREINO:
1. Consulta Nutricional + Treino Completo — R$ 620,00
   Avaliação inicial + treino personalizado + plano alimentar + retorno após 30 dias

2. Pacote Trimestral Nutrição + Treino Premium — R$ 1.120,00 (o mais popular)
   3 meses, treino periodizado, 3 retornos (30 dias), suporte prioritário

3. Plano Semestral Nutrição + Treino Alta Performance — R$ 2.020,00
   6 meses, treinos personalizados e periodizados, 6 retornos, suporte premium

4. Consulta em grupo com treino (desconto com amigos):
   Com 1 amigo: R$ 560,00 por pessoa
   Com 2 amigos: R$ 500,00 por pessoa
   Obs.: todas as consultas do grupo devem ser no mesmo dia

DÚVIDAS FREQUENTES:
- Duração da consulta: 60 a 90 minutos
- Retorno: após 30 dias, com duração de 30 minutos (nova avaliação + dúvidas)
- Máximo de 2 amigos por consulta em grupo
- Acompanhamento via aplicativo Web Diet (dieta passada para o app)

OBSERVAÇÕES IMPORTANTES:
- Não atendemos menores de 16 anos
- Não atendemos gestantes
- Não aceitamos convênios (apenas particular)
- No agendamento: pagamento de 50% do valor antecipado (não reembolsável)

REGRAS DE COMPORTAMENTO:
- Nunca invente informações sobre tratamentos ou diagnósticos
- Não faça promessas de resultados específicos (ex: "você vai perder X kg")
- Para agendar, instrua o paciente a digitar 1
- Para cancelar, instrua o paciente a digitar 2
- Respostas curtas, máximo 3 parágrafos
- Nunca use markdown (negrito, itálico, listas com *) — só texto simples
- Se não souber responder, oriente o paciente a falar diretamente com o Paulo: +55 38 99953-8226
""".strip()

PROMPT_INTERPRETAR_DATA = """
O paciente disse: "{mensagem}"

Hoje é {hoje} ({hoje_nome}).

Extraia a data mencionada. Regras:
- Dia da semana sem contexto (ex: "quarta", "quarta feira", "sexta") → próximo dia da semana a partir de amanhã
- "amanhã" → dia seguinte
- "hoje" → dia de hoje
- "próxima semana" → 7 dias à frente
- DD/MM ou DD/MM/AAAA → use direto

Responda SOMENTE o JSON abaixo, sem nenhum texto antes ou depois:
{{"data": "DD/MM/AAAA", "sucesso": true}}

Se não conseguir identificar, retorne exatamente:
{{"data": null, "sucesso": false}}
"""


def responder_livre(mensagem: str) -> str:
    """
    Gera uma resposta livre para mensagens fora do fluxo de agendamento.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=mensagem,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=600,
                temperature=0.7,
            ),
        )
        return response.text.strip()

    except Exception:
        logger.exception("Erro ao chamar Gemini (responder_livre)")
        return (
            "Desculpe, estou com uma instabilidade no momento. "
            "Para agendar uma consulta, digite 1. "
            "Para cancelar, digite 2."
        )


def interpretar_data(mensagem: str, hoje: str, hoje_nome: str) -> dict:
    """
    Interpreta uma mensagem em linguagem natural e extrai a data.
    Retorna dict com: {"data": "DD/MM/AAAA", "sucesso": bool}
    """
    # Tenta fallback local primeiro (mais rápido e confiável para casos comuns)
    resultado_local = _fallback_data_local(mensagem)
    if resultado_local:
        return resultado_local

    try:
        client = _get_client()
        prompt = PROMPT_INTERPRETAR_DATA.format(
            mensagem=mensagem, hoje=hoje, hoje_nome=hoje_nome
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=100,
                temperature=0,
            ),
        )

        texto = response.text.strip()
        logger.info("Gemini interpretar_data raw: %s", texto[:200])
        texto = texto.replace("```json", "").replace("```", "").strip()
        import re
        match = re.search(r'\{[^{}]+\}', texto, re.DOTALL)
        if match:
            texto = match.group(0)
        return json.loads(texto)

    except Exception:
        logger.exception("Erro ao interpretar data com Gemini")
        return {"data": None, "sucesso": False}

PROMPT_DETECTAR_INTENCAO = """
Contexto: o bot perguntou ao cliente se ele gostaria de agendar uma consulta ou tinha alguma dúvida.

O cliente respondeu: "{mensagem}"

Classifique a intenção em uma palavra:

- "agendar": cliente quer marcar/agendar consulta. Exemplos: "quero", "sim", "1", "gostaria de agendar", "vou agendar", "pode marcar", "quero sim", "claro", "gostaria"
- "recusar": cliente não quer agendar agora. Exemplos: "não", "obrigado", "tchau", "depois", "n"  
- "duvida": cliente faz uma PERGUNTA ou pede informação. Exemplos: "como funciona?", "qual o preço?", "ok, como funcionam os retornos"

Regra principal: se há uma pergunta (?) ou palavras como "como", "qual", "quanto", "o que", "quando" → é "duvida".
Se é uma afirmação curta de interesse sem pergunta → é "agendar".

Responda APENAS com uma palavra: agendar, recusar ou duvida
"""


def _extrair_texto(response) -> str:
    """Extrai o texto da resposta do Gemini de forma segura."""
    try:
        return response.text or ""
    except Exception:
        return ""


# Mensagens EXATAS que indicam intenção clara de agendar ou recusar
_EXATO_AGENDAR = {
    "1", "sim", "s",
    "agendar", "marcar",
    "quero agendar", "vou agendar", "quero marcar",
    "gostaria de agendar", "gostaria de marcar",
    "quero", "quero sim", "pode agendar", "pode marcar",
    "vamos", "vamos agendar", "claro", "pode ser",
}
_EXATO_RECUSAR = {"2", "não", "nao", "n", "obrigado", "obg", "tchau", "até", "ate"}


def detectar_intencao(mensagem: str) -> str:
    """
    Detecta a intenção do cliente: 'agendar', 'recusar' ou 'duvida'.
    Tenta via Gemini; se falhar, usa palavras-chave exatas como fallback.
    """
    # Fallback apenas para mensagens curtas e exatas (evita falsos positivos em perguntas)
    msg_lower = mensagem.strip().lower()
    if msg_lower in _EXATO_AGENDAR:
        return "agendar"
    if msg_lower in _EXATO_RECUSAR:
        return "recusar"

    try:
        client = _get_client()
        prompt = PROMPT_DETECTAR_INTENCAO.format(mensagem=mensagem)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=10,
                temperature=0,
            ),
        )

        texto = _extrair_texto(response).strip().lower()
        if texto in ("agendar", "recusar", "duvida"):
            return texto
        return "duvida"

    except Exception:
        logger.exception("Erro ao detectar intenção com Gemini")
        return "duvida"