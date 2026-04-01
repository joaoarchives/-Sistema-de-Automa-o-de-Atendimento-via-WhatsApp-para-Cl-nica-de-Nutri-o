"""
Simulação de conversa com o bot no terminal.
Útil para testar o fluxo manualmente sem precisar do WhatsApp.

Uso:
    python scripts/simular_conversa.py
"""
from services.bot import processar_mensagem

TELEFONE = "61999999999"

print("Simulando conversa com o bot. Digite 'sair' para encerrar.\n")

while True:
    msg = input("Você: ").strip()
    if msg.lower() == "sair":
        break

    resposta = processar_mensagem(TELEFONE, msg)
    print(f"Bot: {resposta}\n")