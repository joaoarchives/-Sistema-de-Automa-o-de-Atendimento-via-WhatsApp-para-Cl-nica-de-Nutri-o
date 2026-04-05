import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from services.bot import processar_mensagem

telefone = "5561999999999"

print("Bot iniciado. Digite 'sair' para encerrar.\n")

while True:
    msg = input("Você: ")
    if msg.lower() == "sair":
        break

    resposta = processar_mensagem(telefone, msg)

    print(f"Bot: {resposta.texto}")

    if resposta.tipo == "lista":
        i = 1
        for secao in resposta.lista_secoes:
            print(f"\n  [{secao['title']}]")
            for row in secao["rows"]:
                print(f"  {i} - {row['title']}")
                i += 1
        print(f"\n  (No WhatsApp aparecerá como lista clicável)")

    print()