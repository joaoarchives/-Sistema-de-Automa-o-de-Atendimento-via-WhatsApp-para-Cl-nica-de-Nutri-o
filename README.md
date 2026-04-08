# whatsapp-clinica-bot

Sistema de atendimento e agendamento para o consultório Paulo Jordão, com bot no WhatsApp, painel administrativo web e rotinas agendadas de operação.

## Visão geral

O projeto atende dois fluxos principais:

- atendimento automatizado no WhatsApp, com boas-vindas, dúvidas, agendamento, pagamento, confirmação e lembretes
- painel interno para acompanhar agenda, histórico, conversas e ações operacionais

Áreas principais do sistema:

- `Painel`: login, agenda do dia, agenda da semana, histórico e conversas
- `Agenda`: consultas do dia, semana, confirmação, cancelamento e conclusão
- `Conversas`: timeline por paciente com mensagens, anexos, imagens e documentos
- `WhatsApp`: webhook, mensagens de texto, listas interativas, anexos e status
- `Pagamentos`: instruções de PIX/cartão, envio de comprovante e confirmação pelo painel
- `Scheduler`: expiração de pagamento, lembretes e resumo diário

## Funcionalidades

### Bot e WhatsApp

- envio de boas-vindas
- envio do PDF de planos
- fluxo guiado de agendamento por estados
- interpretação de datas em linguagem natural
- listas interativas para plano, tipo, período, horário, sexo e confirmação
- recebimento de comprovantes em imagem ou documento
- respostas livres com Gemini para dúvidas abertas
- confirmação de pagamento enviada pelo painel
- envio de localização da clínica
- envio de recomendações pré-consulta após confirmação do pagamento
- deduplicação persistente de mensagens recebidas no webhook

### Painel administrativo

- autenticação com JWT
- agenda do dia
- agenda da semana
- histórico paginado
- confirmação de pagamento
- cancelamento e conclusão de consultas
- tela de conversas com visual de chat
- renderização correta de mensagens do paciente e do bot
- preview de imagem e abertura/download de anexos
- layout responsivo para desktop e mobile

### Scheduler

- cancelamento automático de consultas com pagamento expirado
- envio de lembretes próximos do horário da consulta
- envio de resumo diário
- lock exclusivo no MySQL para evitar duplicação de jobs
- heartbeat e health snapshot do processo dedicado

## Stack

### Frontend

- React 19
- React Router DOM 7
- Vite 8
- Axios
- Lucide React

### Backend

- Python 3.11
- Flask 3
- Flask-CORS
- PyJWT
- APScheduler
- Gunicorn
- google-genai
- mysql-connector-python

### Banco

- MySQL

### Testes

- `pytest` no backend
- build do frontend com `vite build`

### Observações reais do repositório

- o frontend compilado é servido pelo backend em produção
- o webhook usa HMAC com assinatura `X-Hub-Signature-256`
- o scheduler não roda dentro do web process
- o container final usa um `entrypoint.sh` com seleção por `APP_ROLE`

## Estrutura do projeto

```text
whatsapp-clinica-bot/
├── backend/
│   ├── api.py
│   ├── app.py
│   ├── entrypoint.sh
│   ├── run_scheduler.py
│   ├── requirements.txt
│   ├── config/
│   │   └── settings.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   ├── runtime_guards.py
│   │   ├── estados.py
│   │   ├── consultas.py
│   │   ├── clientes.py
│   │   └── mensagens.py
│   ├── services/
│   │   ├── bot.py
│   │   ├── gemini.py
│   │   ├── scheduler.py
│   │   ├── whatsapp.py
│   │   └── ...
│   ├── tests/
│   └── assets/
├── frontend/
│   ├── package.json
│   ├── .env.example
│   ├── src/
│   └── public/
├── Dockerfile
└── README.md
```

## Como rodar localmente

## Requisitos

- Python 3.11
- Node.js 20 ou superior
- MySQL acessível

## Backend

```bash
cd backend
python -m venv ..\.venv
..\ .venv\Scripts\activate
pip install -r requirements.txt
```

No Linux/macOS:

```bash
source ../.venv/bin/activate
```

Inicialização local:

```bash
cd backend
python app.py
```

Backend padrão:

- URL local: `http://localhost:5000`
- healthcheck: `GET /health`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend padrão:

- URL local: `http://localhost:5173`
- login: [http://localhost:5173/login](http://localhost:5173/login)

## Variáveis de ambiente

O repositório traz `frontend/.env.example`, mas não traz `.env.example` do backend. A lista abaixo foi inferida diretamente do código atual.

### Frontend

```env
VITE_API_URL=http://localhost:5000
```

### Backend

```env
# Segurança do painel
SECRET_KEY=uma-chave-forte
MEDICO_USER=drpaulo
MEDICO_PASS_HASH=
MEDICO_PASS=
LOGIN_MAX_TENTATIVAS=5
LOGIN_BLOQUEIO_MINUTOS=15
HISTORICO_MAX_POR_PAGINA=100

# Backend / deploy
PORT=5000
FRONTEND_URL=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:5000
RAILWAY_PUBLIC_DOMAIN=
APP_ROLE=web

# Webhook WhatsApp
WEBHOOK_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
WEBHOOK_APP_SECRET=
META_APP_SECRET=
META_WEBHOOK_SECRET=

# WhatsApp Cloud API
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_VERSION=v23.0
WHATSAPP_ALLOW_MOCK=false

# Gemini
GEMINI_API_KEY=
GEMINI_TIMEOUT_SECONDS=12
GEMINI_MAX_WORKERS=4

# Pagamento
PIX_CHAVE=
CARTAO_LINK=
PAGAMENTO_NOTIFICACAO_LOCK_MINUTOS=2

# PDF / assets públicos
PDF_PLANOS_URL=

# Banco
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=clinica
DB_CONNECTION_TIMEOUT=10
DB_POOL_ACQUIRE_TIMEOUT=3
DB_POOL_ACQUIRE_RETRY_INTERVAL=0.05
DB_POOL_SIZE=
DB_POOL_RESET_SESSION=true

# Scheduler
SCHEDULER_LOCK_NAME=whatsapp-clinica-bot:scheduler
SCHEDULER_LOCK_HEARTBEAT_SECONDS=5
SCHEDULER_HEALTH_FILE=/tmp/whatsapp-clinica-bot-scheduler-health.json
```

### Observações importantes

- `MEDICO_PASS_HASH` é o formato preferencial para produção
- `MEDICO_PASS` ainda existe como compatibilidade
- para o webhook HMAC funcionar, pelo menos um destes secrets precisa existir:
  - `WHATSAPP_APP_SECRET`
  - `WEBHOOK_APP_SECRET`
  - `META_APP_SECRET`
  - `META_WEBHOOK_SECRET`
- `WEBHOOK_VERIFY_TOKEN` é usado no `GET /webhook`, não substitui o secret HMAC
- `WHATSAPP_ALLOW_MOCK=true` só faz sentido em ambiente local de desenvolvimento

## Banco de dados

Criação básica:

```sql
CREATE DATABASE clinica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Inicialização de schema/dados:

```bash
cd backend
python database/init_db.py
```

Além disso, o backend também executa `init_db()` antes das rotas de aplicação, para garantir schema mínimo no startup operacional.

## Testes

### Backend

```bash
cd backend
pytest tests -q
```

### Frontend

```bash
cd frontend
npm run build
```

Também existe:

```bash
cd frontend
npm run lint
```

Observações:

- o repositório não traz testes automatizados de frontend
- a cobertura atual do backend inclui webhook, bot, API, scheduler e fluxos principais

## Deploy em produção

## Arquitetura de runtime

Existem dois processos distintos:

- `web`
- `scheduler`

O `scheduler` não roda dentro do `web process`.

Isso está implementado em:

- [Dockerfile](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/Dockerfile)
- [entrypoint.sh](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/entrypoint.sh)
- [run_scheduler.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/run_scheduler.py)

## Processo web

Use:

```env
APP_ROLE=web
```

Comportamento esperado no startup:

```text
[startup] app_role=web
[startup] processo web selecionado; scheduler desabilitado neste processo
```

O web process sobe Gunicorn com `gthread` e atende:

- frontend compilado
- rotas `/api/*`
- `GET /webhook`
- `POST /webhook`

## Processo scheduler

Use:

```env
APP_ROLE=scheduler
```

Comportamento esperado no startup:

```text
[startup] app_role=scheduler
[startup] iniciando processo dedicado do scheduler
Entrypoint do scheduler iniciado - app_role=scheduler ...
Tentando adquirir lock exclusivo do scheduler ...
Lock do scheduler adquirido ...
Job registrado no scheduler ...
Scheduler iniciado em processo dedicado ...
```

## Como verificar se o scheduler está ativo

Sinais objetivos:

1. logs do processo dedicado
2. lock exclusivo adquirido
3. arquivo de health snapshot atualizado

### Logs esperados

- `Lock do scheduler adquirido`
- `Job registrado no scheduler`
- `Scheduler iniciado em processo dedicado e pronto para executar jobs`

### Health snapshot

Arquivo padrão:

```text
/tmp/whatsapp-clinica-bot-scheduler-health.json
```

Pode ser sobrescrito por:

```env
SCHEDULER_HEALTH_FILE=/caminho/desejado/scheduler-health.json
```

Conteúdo esperado no arquivo:

- `status`
- `app_role`
- `hostname`
- `pid`
- `lock_name`
- `lock_acquired`
- `scheduler_running`
- `heartbeat_at`
- `jobs`

Estados esperados:

- `starting`
- `running`
- `standby`
- `unhealthy`
- `stopped`

## Exemplo de deploy com dois serviços

### Serviço web

```env
APP_ROLE=web
```

### Serviço scheduler

```env
APP_ROLE=scheduler
```

Ambos precisam compartilhar:

- mesmas variáveis de banco
- mesmas variáveis do WhatsApp
- mesma configuração de segurança aplicável

## Webhook e segurança

## Webhook

O projeto expõe:

- `GET /webhook`
- `POST /webhook`

No `POST /webhook`:

- valida HMAC com `X-Hub-Signature-256`
- falha fechado se o secret estiver ausente
- retorna `403` para assinatura inválida
- deduplica mensagens por `message_id`

## Segurança e operação

- use `SECRET_KEY` forte em produção
- prefira `MEDICO_PASS_HASH` a `MEDICO_PASS`
- o login do painel tem rate limiting e bloqueio temporário
- o webhook possui deduplicação persistente
- o scheduler usa lock exclusivo no MySQL
- os logs atuais não imprimem secrets ou valores de teste

## Fluxo principal

1. paciente envia mensagem no WhatsApp
2. webhook valida assinatura e deduplica a entrada
3. bot conduz o fluxo por estado
4. consulta é criada em `aguardando_pagamento`
5. paciente envia comprovante
6. painel confirma pagamento
7. sistema envia confirmação e recomendações
8. scheduler executa expiração, lembretes e resumo diário

## Observações de produção

## O que monitorar nas primeiras horas

- logs do `web` e do `scheduler`
- respostas do `POST /webhook`
- erro de assinatura HMAC
- aquisição do lock do scheduler
- atualização do `SCHEDULER_HEALTH_FILE`
- falhas de envio ao WhatsApp
- falhas de conexão/pool do MySQL

## Comportamento esperado do webhook

- mensagens válidas entram no fluxo e geram resposta
- mensagens duplicadas com mesmo `message_id` são ignoradas
- mensagens com assinatura inválida são recusadas

## Comportamento esperado do scheduler

- apenas o processo com `APP_ROLE=scheduler` tenta registrar jobs
- apenas um processo mantém o lock exclusivo
- se o lock for perdido, o processo encerra

## Riscos residuais reais

- o scheduler depende de um processo dedicado subir de fato em produção
- o webhook depende de secret HMAC correto e token da Meta válidos
- o repositório ainda não traz `.env.example` do backend
- não há testes automatizados de frontend

## Scripts úteis

Simulador local do bot:

```bash
python teste_bot.py
```

## Licença

Nenhuma licença foi encontrada na raiz do repositório até esta revisão.

## Notas desta documentação

### Arquivos usados como fonte

- [Dockerfile](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/Dockerfile)
- [entrypoint.sh](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/entrypoint.sh)
- [app.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/app.py)
- [api.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/api.py)
- [settings.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/config/settings.py)
- [connection.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/database/connection.py)
- [init_db.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/database/init_db.py)
- [runtime_guards.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/database/runtime_guards.py)
- [bot.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/services/bot.py)
- [whatsapp.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/services/whatsapp.py)
- [gemini.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/services/gemini.py)
- [scheduler.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/services/scheduler.py)
- [run_scheduler.py](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/backend/run_scheduler.py)
- [package.json](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/frontend/package.json)
- [frontend/.env.example](C:/Users/Joaos/OneDrive/Área%20de%20Trabalho/workspace/whatsapp-clinica-bot/frontend/.env.example)

### Pontos inferidos diretamente do código

- o web process e o scheduler usam a mesma imagem e se separam por `APP_ROLE`
- o scheduler escreve health snapshot local em arquivo JSON
- o secret HMAC pode vir por aliases diferentes
- o painel em produção é servido pelo backend com `frontend/dist`

### Informações ainda ausentes no repositório

- `.env.example` do backend
- licença
- documentação oficial do ambiente Railway no próprio repositório
- playbook operacional de incidentes
