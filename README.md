# WhatsApp Clinica Bot

Bot de atendimento e agendamento via WhatsApp para clinica de nutricao, com painel web para gerenciamento das consultas.

## Visao geral

O projeto automatiza o fluxo principal de atendimento:

- recepcao da primeira mensagem do paciente
- envio automatico da tabela de planos em PDF
- respostas em linguagem natural com Gemini
- agendamento guiado por listas interativas
- recebimento de comprovante de pagamento
- confirmacao da consulta pelo painel
- historico de mensagens e consultas no sistema

## Stack

- Backend: Python 3.11, Flask, APScheduler, MySQL
- IA: Google Gemini (`gemini-2.5-flash` por padrao)
- Frontend: React + Vite
- Mensageria: WhatsApp Cloud API
- Deploy: Docker + Gunicorn

## Estrutura do repositorio

```text
whatsapp-clinica-bot-main/
??? backend/
?   ??? app.py
?   ??? api.py
?   ??? config/
?   ??? database/
?   ??? services/
?   ?   ??? agendamento_service.py
?   ?   ??? bot.py
?   ?   ??? bot_content.py
?   ?   ??? bot_lists.py
?   ?   ??? bot_outbound.py
?   ?   ??? bot_response.py
?   ?   ??? gemini.py
?   ?   ??? scheduler.py
?   ?   ??? whatsapp.py
?   ??? tests/
?   ??? requirements.txt
??? frontend/
?   ??? src/
?   ??? package.json
?   ??? .env.example
??? banco de dados/
??? Dockerfile
??? README.md
```

## Melhorias recentes no backend

O fluxo principal do bot foi reorganizado para ficar mais facil de manter:

- `services/bot.py`: dispatcher e handlers principais
- `services/bot_content.py`: textos, constantes e helpers de conteudo
- `services/bot_lists.py`: fabrica de listas interativas do WhatsApp
- `services/bot_outbound.py`: envios iniciais e registro das mensagens automaticas

Tambem foram aplicadas melhorias operacionais:

- suporte a `GEMINI_MODEL` com padrao `gemini-2.5-flash`
- fallback mais seguro quando o Gemini falha ou responde de forma incompleta
- parse mais robusto das mensagens para o painel
- registro da primeira mensagem automatica e do PDF no historico
- resposta com localizacao da clinica quando solicitada ou apos marcacao

## Variaveis de ambiente

Crie um arquivo `.env` na raiz do projeto ou configure as variaveis no ambiente de deploy.

Backend:

- `SECRET_KEY`
- `WEBHOOK_VERIFY_TOKEN`
- `WHATSAPP_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_API_VERSION`
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `PIX_CHAVE`
- `CARTAO_LINK`
- `PDF_PLANOS_URL`
- `MEDICO_USER`
- `MEDICO_PASS`
- `FRONTEND_URL`
- `PORT`

Frontend:

- `VITE_API_URL`

## Como rodar localmente

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

O backend sobe por padrao em `http://localhost:5000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend sobe por padrao em `http://localhost:5173`.

## Docker

O `Dockerfile` da raiz gera o build do frontend e sobe o backend Flask com Gunicorn usando a pasta `backend`.

Exemplo:

```bash
docker build -t whatsapp-clinica-bot .
docker run --env-file .env -p 5000:5000 whatsapp-clinica-bot
```

## Observacoes sobre testes

Os modulos principais do backend estao compilando normalmente. A suite `pytest` existente no repositorio ainda precisa de revisao porque parte dos testes esta acoplada a contratos antigos do bot e parte tenta usar MySQL local sem mocks completos.

## Publicacao no GitHub

Antes de publicar, vale conferir:

- se o `.env` real nao esta no repositorio
- se nao ha credenciais fixas em arquivos locais
- se o deploy vai apontar para `backend/` e nao para `backend/`
- se os artefatos gerados (`__pycache__`, `.pytest_cache`, builds`) ficaram fora do commit
