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
Você é a assistente virtual da Clínica NutriVida, uma clínica de nutrição.
Seu nome é Nutri e você atende pacientes via WhatsApp.

Sobre a clínica:
- Especialidade: Nutrição clínica e esportiva
- Atendimento: Segunda a sábado
- Horários: Manhã (08h às 12h) e Tarde (13h às 17h)
- Médico responsável: Dr. Paulo

Suas responsabilidades:
- Responder dúvidas sobre nutrição de forma clara e acessível
- Explicar como funciona o processo de agendamento
- Orientar o paciente quando ele escrever de forma livre
- Ser sempre gentil, profissional e objetivo

Regras importantes:
- Nunca invente informações sobre tratamentos ou diagnósticos
- Para agendamentos, instrua o paciente a digitar "agendar" ou "1"
- Para cancelamentos, instrua o paciente a digitar "cancelar" ou "2"
- Respostas curtas — máximo 3 parágrafos
- Escreva em português brasileiro informal mas profissional
- Nunca use markdown (negrito, itálico, listas com *) — só texto simples
""".strip()

PROMPT_INTERPRETAR_DATA = """
O paciente disse: "{mensagem}"

Extraia a data e o período (manhã ou tarde) dessa mensagem.
Hoje é {hoje}.

Responda APENAS em JSON nesse formato exato, sem explicações:
{{"data": "DD/MM/AAAA", "periodo": "manha" ou "tarde", "sucesso": true ou false}}

Se não conseguir identificar a data ou o período, retorne:
{{"data": null, "periodo": null, "sucesso": false}}
"""


def responder_livre(mensagem: str) -> str:
    """
    Gera uma resposta livre para mensagens fora do fluxo de agendamento.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=mensagem,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=300,
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


def interpretar_data_periodo(mensagem: str, hoje: str) -> dict:
    """
    Interpreta uma mensagem em linguagem natural e extrai data e período.
    Retorna dict com: {"data": "DD/MM/AAAA", "periodo": "manha"/"tarde", "sucesso": bool}
    """
    try:
        client = _get_client()
        prompt = PROMPT_INTERPRETAR_DATA.format(mensagem=mensagem, hoje=hoje)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=100,
                temperature=0,
            ),
        )

        texto = response.text.strip()
        texto = texto.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)

    except Exception:
        logger.exception("Erro ao interpretar data/período com Gemini")
        return {"data": None, "periodo": None, "sucesso": False}