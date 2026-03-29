from services.bot import processar_mensagem

telefone = "61999999999"

while True:
    msg = input("Você: ")
    if msg.lower() == "sair":
        break

    resposta = processar_mensagem(telefone, msg)
    print(f"Bot: {resposta}")