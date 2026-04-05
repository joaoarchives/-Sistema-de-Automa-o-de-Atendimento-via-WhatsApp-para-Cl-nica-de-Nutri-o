"""
Dispara o resumo diário do médico manualmente.
Útil para testar sem esperar o scheduler rodar às 06h.

Uso:
    python scripts/enviar_resumo.py
"""
from services.notificacoes_medico import enviar_resumo_das_06

enviar_resumo_das_06()