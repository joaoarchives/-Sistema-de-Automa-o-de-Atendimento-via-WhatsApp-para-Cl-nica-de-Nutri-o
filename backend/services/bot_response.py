"""
Representa a resposta do bot para o webhook.

tipo = "texto"  → mensagem de texto simples
tipo = "lista"  → lista interativa clicável do WhatsApp (horários)
"""
from dataclasses import dataclass, field


@dataclass
class BotResponse:
    texto: str
    tipo: str = "texto"          # "texto" | "lista"
    lista_botao: str = "Ver horários"
    lista_secoes: list = field(default_factory=list)

    def __str__(self) -> str:
        """Compatibilidade retroativa: str(resposta) devolve o texto."""
        return self.texto