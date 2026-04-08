# WhatsApp Clínica Bot

Bot de atendimento via WhatsApp para clínica de nutrição, com painel administrativo web integrado. Automatiza agendamentos, cobranças, lembretes e comunicação com pacientes via API oficial do WhatsApp (Meta Cloud API), com IA conversacional via Google Gemini.

---

## Visão Geral

O sistema atende pacientes diretamente pelo WhatsApp através da assistente virtual **Sofia**, conduzindo o fluxo completo de agendamento: escolha de plano, tipo de consulta, data, horário, coleta de dados pessoais e instruções de pagamento. Após a confirmação do pagamento pelo painel, o paciente recebe automaticamente uma mensagem de confirmação e as recomendações pré-consulta.

O **painel administrativo** (React SPA) é servido pelo próprio backend Flask e permite ao médico visualizar a agenda do dia, agenda semanal, histórico paginado de consultas, e todo o histórico de conversas por paciente — incluindo anexos de imagens e documentos enviados via WhatsApp.

**Processos em produção:**

| Processo | Função |
|---|---|
| `web` | Flask + Gunicorn: API REST, webhook WhatsApp, servir frontend |
| `scheduler` | APScheduler dedicado: expiração de pagamentos, lembretes, resumo diário |

Os dois processos são **obrigatoriamente separados**. O scheduler nunca roda dentro do processo web.

---

## Funcionalidades Principais

### Painel Administrativo
- Autenticação via JWT (token expira em 8 horas)
- Rate limiting no login: bloqueio após `LOGIN_MAX_TENTATIVAS` tentativas por combinação IP+usuário
- Agenda do dia com filtro por status e data arbitrária
- Agenda semanal agrupada por dia
- Histórico paginado de todas as consultas
- Confirmação de pagamento com envio automático de WhatsApp ao paciente
- Cancelamento de consulta com motivo
- Conclusão de consulta

### Bot WhatsApp (Sofia)
- Fluxo guiado de agendamento completo via estados persistidos no banco
- Interpretação de datas em linguagem natural via Google Gemini
- Respostas livres sobre nutrição e a clínica via Gemini
- Envio do PDF de planos no primeiro contato
- Envio de localização da clínica
- Instruções de pagamento com lista interativa
- Recebimento e processamento de comprovante (imagem/documento)
- Mensagens interativas (listas e botões)

### Conversas no Painel
- Listagem de todas as conversas com prévia da última mensagem
- Histórico completo de mensagens por paciente (enviadas e recebidas)
- Exibição de imagens e documentos enviados pelo paciente via WhatsApp (proxy autenticado via `/api/conversas/media/<media_id>`)
- Inferência automática de direção da mensagem (client/bot)

### Automações (Scheduler)
| Job | Frequência | Ação |
|---|---|---|
| `expirar_pagamentos` | A cada 5 min | Cancela consultas `aguardando_pagamento` com prazo expirado (1h); notifica paciente |
| `verificar_lembretes` | A cada 1 min | Verifica consultas confirmadas elegíveis e envia lembretes apenas nos marcos de 24h e 12h antes da consulta |
| `enviar_resumo_do_dia` | Diário às 06:00 | Envia resumo da agenda do dia ao médico via WhatsApp |

### Segurança
- Webhook com validação de assinatura HMAC-SHA256 (`X-Hub-Signature-256`)
- Deduplicação de webhooks via tabela `webhook_dedup` no MySQL
- Rate limiting de login persistido em `auth_login_attempts`
- Lock exclusivo do scheduler via `GET_LOCK()` do MySQL (impede instâncias duplicadas)
- Health snapshot do scheduler em arquivo JSON (`SCHEDULER_HEALTH_FILE`)

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11, Flask 3.0, Gunicorn 23 (gthread) |
| Frontend | React 19, Vite 8, React Router 7, Axios, Lucide React |
| Banco de dados | MySQL (mysql-connector-python) |
| IA conversacional | Google Gemini (`google-genai`, modelo padrão: `gemini-2.5-flash`) |
| Scheduler | APScheduler 3.10 (BackgroundScheduler) |
| Autenticação | PyJWT (HS256) |
| Testes | pytest 8 |
| Container | Docker (multi-stage: Node 20 Alpine + Python 3.11 slim) |

---

## Estrutura do Projeto

```
whatsapp-clinica-bot/
├── Dockerfile                  # Build multi-stage (frontend + backend)
├── backend/
│   ├── app.py                  # Aplicação Flask principal, webhook, rotas estáticas
│   ├── api.py                  # Blueprint /api: autenticação, consultas, conversas
│   ├── run_scheduler.py        # Entrypoint do processo scheduler (APP_ROLE=scheduler)
│   ├── entrypoint.sh           # Seleciona processo: web ou scheduler via APP_ROLE
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── config/
│   │   └── settings.py         # Configuração central via variáveis de ambiente
│   ├── database/
│   │   ├── connection.py       # Pool de conexões MySQL
│   │   ├── init_db.py          # Criação/migração do schema
│   │   ├── clientes.py
│   │   ├── consultas.py
│   │   ├── estados.py          # Estado da conversa por telefone
│   │   ├── mensagens.py        # Log de mensagens WhatsApp
│   │   └── runtime_guards.py   # Rate limit de login e deduplicação de webhook
│   ├── services/
│   │   ├── bot.py              # Máquina de estados do fluxo de conversa
│   │   ├── bot_response.py     # Estrutura de resposta do bot
│   │   ├── agendamento_service.py
│   │   ├── gemini.py           # Integração Google Gemini (datas + respostas livres)
│   │   ├── whatsapp.py         # Envio de mensagens via Meta Cloud API
│   │   ├── scheduler.py        # Definição e registro dos jobs APScheduler
│   │   └── notificacoes_medico.py  # Resumo diário para o médico
│   ├── utils/
│   │   ├── helpers.py
│   │   └── time_utils.py       # Timezone (padrão: America/Sao_Paulo)
│   ├── tests/
│   │   ├── tests_api.py
│   │   ├── tests_app.py
│   │   ├── tests_bot.py
│   │   ├── tests_consultas.py
│   │   ├── tests_run_scheduler.py
│   │   ├── tests_scheduler.py
│   │   └── tests_whatsapp.py
│   ├── assets/
│   │   └── Planos 2026.pdf     # PDF de planos enviado no primeiro contato
│   └── scripts/
│       ├── enviar_resumo.py    # Script utilitário manual
│       └── simular_conversa.py
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api/api.js           # Cliente Axios para o backend
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── AgendaDia.jsx
    │   │   ├── AgendaSemana.jsx
    │   │   ├── Historico.jsx
    │   │   └── Conversas.jsx
    │   └── components/
    │       ├── ConsultaCard.jsx
    │       └── Layout.jsx
    └── .env.example
```

---

## Requisitos

- **Python** 3.11+
- **Node.js** 20+
- **MySQL** 8.0+ (ou compatível)
- Conta **Meta for Developers** com app WhatsApp Business configurado
- Chave de API **Google Gemini** (`GEMINI_API_KEY`)
- Docker (opcional, para deploy containerizado)

---

## Instalação

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm ci
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto (mesmo nível de `backend/` e `frontend/`). O backend carrega este arquivo via `python-dotenv`.

```dotenv
# ── Segurança ────────────────────────────────────────────────────────────────
# Chave usada para assinar tokens JWT do painel. Use no mínimo 32 caracteres aleatórios.
SECRET_KEY=gere_uma_chave_forte_aqui

# ── Painel administrativo ────────────────────────────────────────────────────
# Usuário e senha do médico para acesso ao painel.
# O painel exige MEDICO_PASS_HASH; MEDICO_PASS em texto puro não é aceito.
MEDICO_USER=medico
MEDICO_PASS_HASH=pbkdf2:sha256:...   # gere com: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('suasenha'))"

# Máximo de tentativas de login antes do bloqueio (padrão: 5)
LOGIN_MAX_TENTATIVAS=5
# Duração do bloqueio em minutos (padrão: 15)
LOGIN_BLOQUEIO_MINUTOS=15

# ── WhatsApp / Meta Cloud API ────────────────────────────────────────────────
# Token de acesso permanente da conta WhatsApp Business
WHATSAPP_TOKEN=EAAxxxxxxxx

# ID do número de telefone registrado no Meta
WHATSAPP_PHONE_NUMBER_ID=1234567890

# Token escolhido por você para verificação do webhook no painel Meta
WEBHOOK_VERIFY_TOKEN=meu_token_de_verificacao

# Segredo do app Meta (App Secret) para validação HMAC da assinatura do webhook.
# O sistema aceita qualquer uma das variáveis abaixo (na ordem de prioridade):
# WHATSAPP_APP_SECRET | WEBHOOK_APP_SECRET | META_APP_SECRET | META_WEBHOOK_SECRET
WHATSAPP_APP_SECRET=segredo_do_app_meta

# Versão da API (padrão: v23.0)
WHATSAPP_API_VERSION=v23.0

# ── Google Gemini ────────────────────────────────────────────────────────────
GEMINI_API_KEY=AIzaSyxxxxxxxx
# Modelo a usar (padrão: gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash
# Timeout em segundos para chamadas ao Gemini (padrão: 12)
GEMINI_TIMEOUT_SECONDS=12

# ── Banco de dados ───────────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=senha_do_banco
DB_NAME=clinica

# Timeouts e pool (opcionais; os padrões funcionam para a maioria dos casos)
DB_CONNECTION_TIMEOUT=10
DB_POOL_ACQUIRE_TIMEOUT=3
DB_POOL_SIZE=6

# ── Processo web (Gunicorn) ──────────────────────────────────────────────────
PORT=5000
WEB_CONCURRENCY=1
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120

# URL do frontend para configuração de CORS (desenvolvimento)
FRONTEND_URL=http://localhost:5173

# ── Processo scheduler ───────────────────────────────────────────────────────
# Define o papel do processo. Valores: "web" (padrão) | "scheduler"
APP_ROLE=web

# Nome do lock MySQL distribuído (padrão suficiente para ambiente single-cluster)
SCHEDULER_LOCK_NAME=whatsapp-clinica-bot:scheduler

# Intervalo do heartbeat do lock em segundos (padrão: 5)
SCHEDULER_LOCK_HEARTBEAT_SECONDS=5

# Caminho do arquivo JSON de health do scheduler
SCHEDULER_HEALTH_FILE=/tmp/whatsapp-clinica-bot-scheduler-health.json

# ── Timezone ─────────────────────────────────────────────────────────────────
APP_TIMEZONE=America/Sao_Paulo

# ── Paginação ────────────────────────────────────────────────────────────────
HISTORICO_MAX_POR_PAGINA=100
```

### Frontend (desenvolvimento)

```bash
# frontend/.env
VITE_API_URL=http://localhost:5000
```

Em produção, o frontend é servido pelo próprio Flask (sem necessidade de `.env` separado).

---

## Execução Local

### 1. Banco de dados

Crie o banco `clinica` no MySQL. O schema é inicializado automaticamente na primeira requisição ao backend.

```sql
CREATE DATABASE clinica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Backend (processo web)

```bash
cd backend
python app.py
# Ou via Gunicorn:
gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --worker-class gthread app:app
```

Acesse: `http://localhost:5000`

### 3. Frontend (desenvolvimento)

```bash
cd frontend
npm run dev
```

Acesse: `http://localhost:5173`

### 4. Scheduler (processo separado)

```bash
cd backend
APP_ROLE=scheduler python run_scheduler.py
```

O scheduler tentará adquirir um lock exclusivo no MySQL. Se outro processo já possuir o lock, ele encerra com código 0 (comportamento esperado em ambientes com múltiplas réplicas).

---

## Testes

```bash
cd backend
pytest
```

Os arquivos de teste estão em `backend/tests/` e cobrem: API, app Flask, bot, consultas, scheduler, run_scheduler e integração WhatsApp.

O `pytest.ini` configura `pythonpath = .` para que os imports funcionem corretamente a partir do diretório `backend/`.

---

## Build e Deploy

### Build da imagem Docker

```bash
docker build -t whatsapp-clinica-bot .
```

O Dockerfile realiza build multi-stage:
1. **Estágio 1** (`node:20-alpine`): executa `npm ci && npm run build` no frontend, gerando `frontend/dist/`
2. **Estágio 2** (`python:3.11-slim`): instala dependências Python, copia o backend e o `frontend/dist` gerado no estágio anterior

O Flask serve o frontend compilado diretamente em `/` (SPA com fallback para `index.html`).

---

### Arquitetura de Deploy

São necessários **dois processos** rodando a partir da mesma imagem:

#### Processo Web

```bash
docker run -e APP_ROLE=web -e PORT=5000 \
  --env-file .env \
  -p 5000:5000 \
  whatsapp-clinica-bot
```

O `entrypoint.sh` detecta `APP_ROLE=web` (padrão) e inicia o Gunicorn:

```
gunicorn --bind 0.0.0.0:$PORT --workers $WEB_CONCURRENCY --threads $GUNICORN_THREADS --worker-class gthread --timeout $GUNICORN_TIMEOUT app:app
```

#### Processo Scheduler

```bash
docker run -e APP_ROLE=scheduler \
  --env-file .env \
  whatsapp-clinica-bot
```

O `entrypoint.sh` detecta `APP_ROLE=scheduler` e executa `python run_scheduler.py`.

> **Importante:** o scheduler **nunca deve rodar no mesmo processo** que o Gunicorn. O processo web não inicia nenhum job APScheduler; toda automação fica exclusivamente no processo scheduler.

---

### Verificando o Scheduler em Produção

**Logs esperados na inicialização:**

```
[startup] app_role=scheduler
[startup] iniciando processo dedicado do scheduler
Tentando adquirir lock exclusivo do scheduler - lock=whatsapp-clinica-bot:scheduler
Lock do scheduler adquirido - lock=... connection_id=...
Inicializando scheduler dedicado - timezone=America/Sao_Paulo jobs=3
Job registrado no scheduler - id=expirar_pagamentos trigger=interval ...
Job registrado no scheduler - id=verificar_lembretes trigger=interval ...
Job registrado no scheduler - id=enviar_resumo_do_dia trigger=cron ...
Scheduler em execucao com 3 job(s) ativos.
```

**Health snapshot** (atualizado a cada `SCHEDULER_LOCK_HEARTBEAT_SECONDS`):

```bash
cat $SCHEDULER_HEALTH_FILE
# ou dentro do container:
cat /tmp/whatsapp-clinica-bot-scheduler-health.json
```

O campo `"status"` deve ser `"running"` e `"scheduler_running": true`. Se `"status": "standby"`, outro processo já possui o lock — comportamento normal em deploys com mais de uma réplica do scheduler.

---

### Plataformas como serviço (Heroku, Render, Railway etc.)

Defina dois serviços/dynos apontando para a mesma imagem:

| Serviço | Variável | Comando efetivo |
|---|---|---|
| `web` | `APP_ROLE=web` | Gunicorn via `entrypoint.sh` |
| `scheduler` | `APP_ROLE=scheduler` | `python run_scheduler.py` via `entrypoint.sh` |

---

## Segurança e Operação

| Mecanismo | Detalhe |
|---|---|
| `SECRET_KEY` | Assina todos os tokens JWT. Use valor aleatório com no mínimo 32 caracteres. Nunca use os placeholders: `chave_secreta`, `dev_secret`, `sua_chave_secreta`, `secret`. Se detectado, o painel retorna 503. |
| Webhook HMAC | Toda requisição POST em `/webhook` é validada via `X-Hub-Signature-256` com o `WHATSAPP_APP_SECRET`. Requisições sem assinatura válida são rejeitadas com 403. |
| Rate limiting de login | Após `LOGIN_MAX_TENTATIVAS` falhas (padrão 5), a combinação IP+usuário é bloqueada por `LOGIN_BLOQUEIO_MINUTOS` (padrão 15). Persistido em MySQL. |
| Deduplicação de webhook | Cada `message_id` recebido é registrado na tabela `webhook_dedup`. Mensagens duplicadas são descartadas silenciosamente. |
| Lock do scheduler | `GET_LOCK()` do MySQL garante que apenas uma instância do scheduler execute os jobs, mesmo com múltiplas réplicas. |
| Senha do painel | Use somente `MEDICO_PASS_HASH` (hash Werkzeug/pbkdf2). `MEDICO_PASS` em texto puro não é aceito. |
| Logs | O sistema loga tentativas de login, webhooks recebidos, mensagens processadas e erros sem expor valores de secrets. |
| Lembretes | O scheduler usa controle explícito por consulta para lembrete_24h_enviado e lembrete_12h_enviado, evitando reenvio do mesmo lembrete. |

---

## Fluxo Principal do Sistema

```
Paciente envia mensagem WhatsApp
         │
         ▼
POST /webhook → validação HMAC → deduplicação → bot.processar_mensagem()
         │
         ▼
Máquina de estados (database/estados.py):
  inicio → boas_vindas (envia PDF de planos)
         → menu → plano → tipo_consulta → data → confirmar_data
         → periodo_livre → horario → nome → sexo → confirmacao
         → aguardando_comprovante (paciente envia imagem/doc)
         → pagamento_em_analise
         │
         ▼ (médico acessa painel)
PATCH /api/consultas/{id}/confirmar-pagamento
  → atualiza status para "confirmado"
  → envia mensagem de confirmação ao paciente via WhatsApp
  → envia recomendações pré-consulta via WhatsApp
  → atualiza estado da conversa para "consulta_confirmada"
         │
         ▼
Scheduler (processo separado):
  - verificar_lembretes: roda a cada 1 minuto, mas só envia lembretes quando a consulta entra exatamente na janela de 24h ou 12h antes
  - expirar_pagamentos: cancela e notifica se 1h sem pagamento
  - enviar_resumo_do_dia: agenda do dia às 06:00 para o médico
```

---

## Monitoramento Inicial em Produção

Nas primeiras horas após o deploy, valide:

1. **`GET /health`** → deve retornar `{"status": "ok"}` com HTTP 200
2. **Verificação do webhook Meta** → `GET /webhook?hub.mode=subscribe&hub.verify_token=...` deve retornar o challenge
3. **Login no painel** → `POST /api/auth/login` com as credenciais configuradas
4. **Health do scheduler** → `cat $SCHEDULER_HEALTH_FILE` deve mostrar `"status": "running"`
5. **Logs do scheduler** → confirmar presença dos 3 jobs registrados e ausência de erros de conexão MySQL
6. **Envio de mensagem de teste** → verificar nos logs do processo web: `Mensagem recebida - de=... tipo=... id=...` e `Resposta do bot gerada`
7. **Assinatura do webhook** → confirmar nos logs: `Webhook secret status - configurado=True origem=WHATSAPP_APP_SECRET comprimento_valido=True`

**Pontos críticos:**
- Se `SECRET_KEY` estiver com valor placeholder, o painel retorna 503 em todas as rotas autenticadas
- Se `WHATSAPP_APP_SECRET` não estiver configurado, todos os webhooks são rejeitados com 503
- Se o banco não estiver acessível, o backend retorna 503 na primeira requisição que necessite de DB

---

## Riscos Residuais / Observações

- **Uma única instância do scheduler por cluster**: o lock MySQL funciona corretamente apenas se todos os processos apontarem para o mesmo banco. Em setups multi-região com bancos separados, pode haver execução duplicada de jobs.
- **Scheduler sem reinício automático**: se o processo scheduler encerrar por perda de lock (código de saída 1), é necessário um supervisor (systemd, Heroku restart policy, etc.) para reiniciá-lo.
- **Estado da conversa em banco**: o estado de cada paciente (`database/estados.py`) é persistido no MySQL. Limpeza periódica de estados antigos não está automatizada no código analisado.
- **`MEDICO_PASS_HASH` obrigatório**: o painel falha fechado com `503` se `MEDICO_USER` ou `MEDICO_PASS_HASH` não estiverem configurados corretamente.

---

## Licença

Uso interno / privado. Todos os direitos reservados.

