"""
Serviço de integração com o Google Gemini (google-genai SDK).
"""
import json
import logging
import os
from datetime import date, timedelta

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - fallback para ambiente sem SDK
    genai = None
    types = None

logger = logging.getLogger(__name__)

_client = None
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

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
    if msg in ("hoje",):
        return {"data": date.today().strftime("%d/%m/%Y"), "sucesso": True}
    if msg in ("amanhã", "amanha"):
        d = date.today() + timedelta(days=1)
        return {"data": d.strftime("%d/%m/%Y"), "sucesso": True}
    for nome, weekday in _DIAS_SEMANA_PT.items():
        if msg == nome or msg.startswith(nome + " "):
            hoje = date.today()
            dias_ate = (weekday - hoje.weekday()) % 7
            if dias_ate == 0:
                dias_ate = 7
            d = hoje + timedelta(days=dias_ate)
            return {"data": d.strftime("%d/%m/%Y"), "sucesso": True}
    return None


def _get_client():
    global _client
    if _client is None:
        if genai is None:
            raise RuntimeError("SDK google-genai nao esta instalado.")

        api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("gemini_api_key")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        if not api_key:
            raise RuntimeError(
                "Nenhuma chave Gemini encontrada. Tente GEMINI_API_KEY, gemini_api_key ou GOOGLE_API_KEY."
            )

        _client = genai.Client(api_key=api_key)
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
2. Pacote Trimestral Premium — R$ 850,00 (o mais popular)
3. Plano Semestral Alta Performance — R$ 1.600,00
4. Consulta em grupo: 1 amigo R$ 400,00 | 2 amigos R$ 360,00 por pessoa

PLANOS — NUTRIÇÃO + TREINO:
1. Consulta Nutricional + Treino Completo — R$ 620,00
2. Pacote Trimestral Nutrição + Treino Premium — R$ 1.120,00 (o mais popular)
3. Plano Semestral Nutrição + Treino Alta Performance — R$ 2.020,00
4. Consulta em grupo: 1 amigo R$ 560,00 | 2 amigos R$ 500,00 por pessoa

OBSERVAÇÕES IMPORTANTES:
- Não atendemos menores de 16 anos
- Não atendemos gestantes
- Não aceitamos convênios (apenas particular)
- No agendamento: pagamento de 50% do valor antecipado (não reembolsável)

ORIENTA??ES SOBRE RETORNOS E ACOMPANHAMENTO:
- N?o confunda tempo do plano/acompanhamento com intervalo entre retornos
- O acompanhamento online pode durar de 60 dias at? 6 meses, conforme o plano escolhido
- Os retornos fazem parte desse acompanhamento dentro do per?odo contratado
- Se o paciente perguntar de quanto em quanto tempo s?o os retornos, n?o invente uma periodicidade fixa
- Quando a frequ?ncia exata n?o estiver definida no contexto, explique que os retornos acontecem dentro do acompanhamento, conforme a necessidade do paciente e a orienta??o do Dr. Paulo
- Se perguntarem sobre prazo de entrega dos protocolos, informe que o plano de dieta e/ou treino ? entregue em at? 48 horas ?teis ap?s a consulta
- N?o diga que voc? n?o tem essa informa??o para perguntas j? definidas aqui

REGRAS DE COMPORTAMENTO:
- Nunca invente informações sobre tratamentos ou diagnósticos
- Não faça promessas de resultados específicos
- Para agendar, instrua o paciente a digitar 1
- Para cancelar, instrua o paciente a digitar 2
- Respostas curtas, máximo 3 parágrafos
- Nunca use markdown — só texto simples
- Se não souber responder, oriente: +55 38 99953-8226
- NUNCA use placeholders como [Nome], [Data] — use apenas informações reais
- NUNCA confirme agendamentos ou pagamentos — isso é feito pelo sistema
""".strip()

PROMPT_INTERPRETAR_DATA = """
O paciente disse: "{mensagem}"

Hoje é {hoje} ({hoje_nome}).

Extraia a data mencionada. Regras:
- Dia da semana (ex: "quarta", "sexta") → próximo dia a partir de amanhã
- "amanhã" → dia seguinte
- "hoje" → dia de hoje
- DD/MM ou DD/MM/AAAA → use direto

Responda SOMENTE o JSON abaixo, sem nenhum texto antes ou depois:
{{"data": "DD/MM/AAAA", "sucesso": true}}

Se não conseguir identificar, retorne exatamente:
{{"data": null, "sucesso": false}}
"""

PROMPT_DETECTAR_INTENCAO = """
Contexto: o bot perguntou ao cliente se ele gostaria de agendar uma consulta ou tinha alguma dúvida.

O cliente respondeu: "{mensagem}"

Classifique a intenção em uma palavra:
- "agendar": cliente quer marcar/agendar consulta
- "recusar": cliente não quer agendar agora
- "duvida": cliente faz uma pergunta ou pede informação

Responda APENAS com uma palavra: agendar, recusar ou duvida
"""

_EXATO_AGENDAR = {
    "1", "sim", "s", "agendar", "marcar",
    "quero agendar", "vou agendar", "quero marcar",
    "gostaria de agendar", "quero", "quero sim",
    "pode agendar", "vamos", "claro", "pode ser",
}
_EXATO_RECUSAR = {"2", "não", "nao", "n", "obrigado", "obg", "tchau", "até", "ate"}


def _extrair_texto(response) -> str:
    try:
        return response.text or ""
    except Exception:
        return ""


def _resposta_parece_incompleta(texto: str) -> bool:
    texto = (texto or "").strip()
    if not texto:
        return True

    finais_ok = (".", "!", "?", '"', "”", ")", "]")
    if texto.endswith(finais_ok):
        return False

    palavras_suspeitas = {
        "sobre", "com", "de", "do", "da", "dos", "das",
        "para", "por", "em", "no", "na", "nos", "nas",
        "os", "as", "eles", "elas",
    }
    ultima = texto.split()[-1].strip(".,!?:;").lower()
    return ultima in palavras_suspeitas or len(texto.split()) < 6


def _gerar_conteudo(
    *,
    prompt: str,
    system_instruction: str | None = None,
    max_output_tokens: int = 500,
    temperature: float = 0.7,
) -> str:
    client = _get_client()

    if types is None:
        raise RuntimeError("SDK google-genai indisponivel.")

    config_kwargs = {
        "max_output_tokens": max_output_tokens,
        "temperature": temperature,
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    texto = _extrair_texto(response).strip()

    finish_reason = None
    try:
        finish_reason = response.candidates[0].finish_reason
    except Exception:
        pass

    logger.info(
        "Gemini response model=%s finish_reason=%s texto=%r",
        _MODEL_NAME,
        finish_reason,
        texto[:500],
    )
    return texto


def responder_livre(mensagem: str) -> str:
    try:
        texto = _gerar_conteudo(
            prompt=mensagem,
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=500,
            temperature=0.7,
        )
        if _resposta_parece_incompleta(texto):
            logger.warning("Resposta do Gemini parece incompleta: %r", texto)
            return (
                "Posso te explicar melhor sobre retornos, prazos de entrega dos protocolos, "
                "planos ou agendamento. Me diga qual ponto voce quer saber primeiro."
            )
        return texto
    except Exception:
        logger.exception("Erro ao chamar Gemini (responder_livre)")
        return (
            "Desculpe, estou com uma instabilidade no momento. "
            "Para agendar uma consulta, digite 1. "
            "Para cancelar, digite 2."
        )


def interpretar_data(mensagem: str, hoje: str, hoje_nome: str) -> dict:
    resultado_local = _fallback_data_local(mensagem)
    if resultado_local:
        return resultado_local
    try:
        import re
        prompt = PROMPT_INTERPRETAR_DATA.format(
            mensagem=mensagem, hoje=hoje, hoje_nome=hoje_nome
        )
        texto = _gerar_conteudo(
            prompt=prompt,
            max_output_tokens=100,
            temperature=0,
        )
        logger.info("Gemini interpretar_data raw: %s", texto[:200])
        texto = texto.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{[^{}]+\}', texto, re.DOTALL)
        if match:
            texto = match.group(0)
        dados = json.loads(texto)
        if isinstance(dados, dict) and "sucesso" in dados:
            return dados
        raise ValueError("Resposta JSON fora do formato esperado.")
    except Exception:
        logger.exception("Erro ao interpretar data com Gemini")
        return {"data": None, "sucesso": False}


def detectar_intencao(mensagem: str) -> str:
    msg_lower = mensagem.strip().lower()
    if msg_lower in _EXATO_AGENDAR:
        return "agendar"
    if msg_lower in _EXATO_RECUSAR:
        return "recusar"
    try:
        prompt = PROMPT_DETECTAR_INTENCAO.format(mensagem=mensagem)
        texto = _gerar_conteudo(
            prompt=prompt,
            max_output_tokens=10,
            temperature=0,
        ).lower()
        if texto in ("agendar", "recusar", "duvida"):
            return texto
        return "duvida"
    except Exception:
        logger.exception("Erro ao detectar intenção com Gemini")
        return "duvida"
