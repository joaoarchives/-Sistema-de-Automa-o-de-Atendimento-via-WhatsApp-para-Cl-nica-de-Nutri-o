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

Extraia a data dessa mensagem. Hoje é {hoje} ({hoje_nome}).

Exemplos: "sexta" → próxima sexta-feira, "amanhã" → dia seguinte, "15/04" → 15/04.

Responda APENAS em JSON nesse formato exato, sem explicações:
{{"data": "DD/MM/AAAA", "sucesso": true}}

Se não conseguir identificar a data, retorne:
{{"data": null, "sucesso": false}}
"""


def _extrair_texto(response) -> str:
    """Extrai o texto da resposta do Gemini de forma segura (suporta modelos com 'thinking')."""
    # Tenta response.text primeiro
    try:
        if response.text:
            return response.text.strip()
    except Exception:
        pass
    # Fallback: percorre os parts e pega apenas os de tipo texto
    try:
        candidates = response.candidates or []
        for part in candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                return part.text.strip()
    except (IndexError, AttributeError, TypeError):
        pass
    return ""


def responder_livre(mensagem: str) -> str:
    """
    Gera uma resposta livre para mensagens fora do fluxo de agendamento.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="models/gemini-2.5-pro",
            contents=mensagem,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=300,
                temperature=0.7,
            ),
        )
        return _extrair_texto(response) or (
            "Desculpe, não consegui gerar uma resposta. "
            "Para agendar, digite 1. Para cancelar, digite 2."
        )

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
    try:
        client = _get_client()
        prompt = PROMPT_INTERPRETAR_DATA.format(
            mensagem=mensagem, hoje=hoje, hoje_nome=hoje_nome
        )

        response = client.models.generate_content(
            model="models/gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=2000,
                temperature=0,
            ),
        )

        texto = _extrair_texto(response)
        logger.info("interpretar_data raw response: %r", texto[:200] if texto else None)
        if not texto:
            return {"data": None, "sucesso": False}
        texto = texto.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)

    except Exception:
        logger.exception("Erro ao interpretar data com Gemini")
        return {"data": None, "sucesso": False}