# whatsapp-clinica-bot

Painel administrativo e automação de atendimento via WhatsApp para o consultório Paulo Jordão.

O projeto combina um backend Flask integrado à WhatsApp Cloud API, um fluxo de conversa com menus interativos para agendamento e um painel React para acompanhar agenda, histórico, pagamentos e conversas com anexos.

## Visão geral

Este sistema foi construído para apoiar o atendimento do consultório no WhatsApp e no painel interno do profissional.

Pelo WhatsApp, o paciente recebe boas-vindas, PDF de planos, respostas a dúvidas, opções de agendamento, instruções de pagamento, localização da clínica e confirmação da consulta. No painel, o profissional acessa agenda do dia, agenda da semana, histórico e a linha do tempo das conversas, incluindo anexos como imagens e documentos.

## Funcionalidades

### WhatsApp e fluxo de atendimento

- Envio automático de boas-vindas e do PDF de planos
- Conversa guiada por estados para:
  - escolha de plano
  - escolha do tipo de consulta
  - interpretação de data
  - seleção de horário
  - coleta de nome e sexo
  - confirmação do agendamento
- Listas interativas do WhatsApp para planos, tipo de consulta, período, horário, sexo e confirmação
- Respostas livres com Gemini para dúvidas fora do fluxo principal
- Interpretação de datas em linguagem natural com fallback local para casos comuns
- Envio de instruções de pagamento com PIX e link de cartão
- Envio da localização da clínica após a confirmação do agendamento
- Recebimento de comprovante em imagem ou documento
- Confirmação posterior do pagamento pelo painel
- Envio de recomendações pré-consulta após a confirmação do pagamento

### Painel administrativo

- Login com JWT
- Agenda do dia
- Agenda da semana
- Histórico paginado
- Confirmação de pagamento, conclusão e cancelamento de consultas
- Feedback visual quando a confirmação do pagamento falha parcialmente ao notificar o paciente
- Tela de conversas em estilo chat, com diferenciação entre mensagens do paciente e do bot
- Visualização de anexos nas conversas
  - preview de imagens
  - abertura/download de documentos
  - proxy autenticado para mídias protegidas do WhatsApp
- Layout responsivo para desktop e mobile

### Segurança e robustez já implementadas

- Rotas do painel protegidas por token JWT
- Rate limiting e bloqueio temporário por tentativas de login
- Deduplicação persistente de mensagens do webhook para evitar reprocessamento
- Proxy de mídia protegido por autenticação do painel
- CORS configurado para as rotas da API

## Stack utilizada

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
- Requests
- google-genai
- Gunicorn

### Banco de dados

- MySQL
- `mysql-connector-python`

### Build e deploy

- Docker multi-stage
- Build do frontend com Node 20 Alpine
- Execução do backend com Gunicorn
- Estrutura compatível com deploy em serviços como Railway

## Estrutura do projeto

```text
whatsapp-clinica-bot/
├── backend/
│   ├── api.py
│   ├── app.py
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── assets/
│   │   └── Planos 2026.pdf
│   ├── config/
│   │   └── settings.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── consultas.py
│   │   ├── clientes.py
│   │   ├── estados.py
│   │   ├── mensagens.py
│   │   ├── runtime_guards.py
│   │   └── init_db.py
│   ├── services/
│   │   ├── agendamento_service.py
│   │   ├── bot.py
│   │   ├── bot_response.py
│   │   ├── gemini.py
│   │   ├── notificacoes_medico.py
│   │   ├── scheduler.py
│   │   └── whatsapp.py
│   ├── tests/
│   │   ├── tests_api.py
│   │   ├── tests_app.py
│   │   └── tests_bot.py
│   └── utils/
│       └── helpers.py
├── banco de dados/
│   └── clinica.sql
├── frontend/
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── public/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       ├── App.jsx
│       ├── index.css
│       └── main.jsx
├── Dockerfile
├── README.md
└── teste_bot.py
```

## Requisitos para rodar

### Recomendados pelo próprio projeto

- Node.js 20 ou superior
- Python 3.11
- MySQL disponível localmente ou em rede

### Necessários para integrações reais

- Conta com WhatsApp Cloud API configurada
- Token e `phone_number_id` válidos da Meta
- Chave do Google Gemini, se quiser respostas livres com IA

## Instalação

### 1. Clonar o projeto

```bash
git clone <url-do-repositorio>
cd whatsapp-clinica-bot
```

### 2. Backend

```bash
cd backend
python -m venv ..\.venv
..\.venv\Scripts\activate
pip install -r requirements.txt
```

Se estiver em Linux ou macOS:

```bash
source ../.venv/bin/activate
```

### 3. Frontend

```bash
cd ../frontend
npm install
```

## Configuração

O backend carrega variáveis de ambiente a partir de um arquivo `.env` na raiz do repositório. O frontend possui um `.env.example` próprio apenas para `VITE_API_URL`.

### Variáveis do backend

O bloco abaixo foi montado a partir do uso real do código em `backend/config/settings.py`, `backend/api.py`, `backend/app.py`, `backend/services/whatsapp.py` e `backend/services/gemini.py`.

```env
# Segurança do painel
SECRET_KEY=troque-por-uma-chave-forte
MEDICO_USER=drpaulo
MEDICO_PASS=troque-por-uma-senha-forte
LOGIN_MAX_TENTATIVAS=5
LOGIN_BLOQUEIO_MINUTOS=15

# Backend / CORS / deploy
PORT=5000
FRONTEND_URL=http://localhost:5173
WEBHOOK_VERIFY_TOKEN=seu-token-de-verificacao
PUBLIC_BASE_URL=http://localhost:5000
RAILWAY_PUBLIC_DOMAIN=

# WhatsApp Cloud API
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_VERSION=v23.0

# Pagamento e materiais enviados ao paciente
PIX_CHAVE=
CARTAO_LINK=
PDF_PLANOS_URL=

# Gemini
GEMINI_API_KEY=

# Banco de dados
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=clinica
```

### Variável do frontend

Arquivo já existente em `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:5000
```

### Observações importantes de configuração

- Se `PDF_PLANOS_URL` não estiver definido, o backend tenta servir o arquivo local `backend/assets/Planos 2026.pdf` via `/assets/Planos%202026.pdf`, usando `PUBLIC_BASE_URL` ou `RAILWAY_PUBLIC_DOMAIN`.
- Se `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID` estiverem ausentes ou com placeholders, as funções de envio do WhatsApp entram em modo local e retornam resposta simulada em vez de chamar a API real.
- O login do painel só funciona se `SECRET_KEY`, `MEDICO_USER` e `MEDICO_PASS` estiverem configurados corretamente.

## Banco de dados

Crie o banco antes da inicialização:

```sql
CREATE DATABASE clinica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Depois inicialize as tabelas e os dados base:

```bash
cd backend
python database/init_db.py
```

Esse script cria, entre outras, as tabelas:

- `clientes`
- `medicos`
- `planos`
- `consultas`
- `estados_conversa`
- `mensagens_whatsapp`
- `auth_login_attempts`
- `webhook_dedup`

Também cria o médico padrão e popula os planos iniciais.

## Como executar localmente

### Backend

Na raiz do repositório, com o ambiente virtual ativo:

```bash
cd backend
python app.py
```

O backend sobe por padrão na porta `5000`.

### Frontend

Em outro terminal:

```bash
cd frontend
npm run dev
```

O Vite sobe por padrão em `http://localhost:5173`.

### Como acessar o painel

- Em desenvolvimento: [http://localhost:5173/login](http://localhost:5173/login)
- Em produção com build servida pelo Flask: `<sua-url>/login`

## Webhook do WhatsApp

O projeto expõe:

- `GET /webhook` para validação do webhook
- `POST /webhook` para recebimento de mensagens e status do WhatsApp

No desenvolvimento local, se quiser integrar de verdade com a Meta, você precisará expor a aplicação publicamente por uma URL HTTPS. O repositório atual não traz uma automação específica para isso; a estratégia depende do ambiente escolhido.

## Testes

### Backend

O backend possui suíte `pytest` em `backend/tests/`.

Para executar:

```bash
cd backend
pytest tests -q
```

Cobertura observável pelos arquivos atuais:

- fluxo do bot
- autenticação e rate limiting da API
- confirmação de pagamento com falha parcial de notificação
- comportamento do webhook, incluindo deduplicação

### Frontend

Não há suíte de testes automatizados de frontend configurada no repositório atual.

Os comandos disponíveis são:

```bash
cd frontend
npm run build
npm run lint
```

## Build e produção

### Build do frontend

```bash
cd frontend
npm run build
```

### Container único com frontend + backend

O `Dockerfile` da raiz faz:

1. build do frontend com Node 20
2. instalação do backend em Python 3.11
3. cópia do `frontend/dist` para dentro da imagem final
4. execução do Flask via Gunicorn

Comando de runtime definido no projeto:

```bash
gunicorn --bind 0.0.0.0:${PORT} app:app
```

### Observações de produção

- O frontend compilado é servido pelo próprio backend Flask.
- O backend também serve os arquivos de `frontend/dist/assets` e, em seguida, os arquivos de `backend/assets`.
- O endpoint `/health` existe e pode ser usado por plataformas de deploy.
- Existe um scheduler em `backend/services/scheduler.py` para expiração de pagamentos, lembretes e resumo diário, mas a inicialização automática dele não aparece no bootstrap principal atual (`backend/app.py`). Antes de produção, vale revisar como esse scheduler será executado no seu ambiente.

## Fluxo principal do sistema

### 1. Primeiro contato

- o paciente envia mensagem para o WhatsApp
- o bot envia boas-vindas
- o sistema tenta enviar o PDF de planos
- o paciente pode seguir para agendamento ou fazer perguntas

### 2. Agendamento

- o paciente escolhe o plano
- escolhe o tipo de consulta
- informa ou descreve a data
- escolhe período e horário disponíveis
- informa nome e sexo
- confirma os dados finais

### 3. Pagamento

Após a confirmação do agendamento, o sistema:

- cria a consulta com status de `aguardando_pagamento`
- envia instruções de pagamento
- envia a localização da clínica
- aguarda o comprovante

### 4. Comprovante e confirmação

- o paciente envia imagem ou documento do comprovante
- o sistema marca a conversa como pagamento em análise
- o profissional confirma o pagamento pelo painel
- o backend atualiza a consulta para `confirmado`
- o sistema envia confirmação final e recomendações pré-consulta ao paciente

### 5. Painel e conversas

No painel, o profissional pode:

- acompanhar a agenda do dia
- navegar pela agenda semanal
- consultar o histórico
- abrir o chat por paciente
- visualizar anexos trocados na conversa
- confirmar pagamento, concluir ou cancelar consultas

## Segurança e observações operacionais

- O painel exige JWT e protege as rotas `/api/*` relevantes com `token_required`.
- O login possui bloqueio por excesso de tentativas, persistido em banco.
- O webhook deduplica `message_id` em banco para evitar reprocessamento após restart.
- A mídia protegida do WhatsApp é exposta ao frontend via proxy autenticado em `/api/conversas/media/<media_id>`.
- O frontend valida a expiração do token no cliente antes de acessar rotas protegidas.
- O projeto usa CORS restrito por `FRONTEND_URL` para `/api/*`.
- O histórico de mensagens do WhatsApp é persistido em `mensagens_whatsapp`.
- Algumas interações do painel ainda usam `alert` e `confirm` nativos do navegador; isso funciona, mas pode ser refinado depois.

## Scripts e utilitários úteis

### Simulador de conversa no terminal

Arquivo da raiz:

```bash
python teste_bot.py
```

Ele importa o backend e permite percorrer o fluxo do bot sem depender do WhatsApp real.

### Scripts adicionais encontrados no repositório

- `backend/scripts/simular_conversa.py`
- `backend/scripts/enviar_resumo.py`
- `backend/listar_modelos.py`

O repositório não documenta formalmente a finalidade operacional de todos esses scripts, então vale revisar cada um antes de incorporá-los ao fluxo de manutenção.

## Melhorias futuras

Sugestões compatíveis com o estado atual do código:

- adicionar testes automatizados de frontend
- definir uma estratégia explícita para execução do scheduler em produção
- substituir `alert` e `confirm` por feedbacks visuais persistentes no painel
- publicar um `.env.example` do backend na raiz do projeto
- documentar melhor scripts auxiliares e rotinas operacionais

## Licença

Nenhuma licença foi encontrada na raiz do repositório no momento desta revisão.

---

## Notas sobre esta documentação

### Fontes usadas para montar este README

- `Dockerfile`
- `frontend/package.json`
- `frontend/.env.example`
- `frontend/vite.config.js`
- `frontend/index.html`
- `frontend/src/App.jsx`
- `frontend/src/api/api.js`
- `frontend/src/components/Layout.jsx`
- `frontend/src/components/ConsultaCard.jsx`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/AgendaDia.jsx`
- `frontend/src/pages/AgendaSemana.jsx`
- `frontend/src/pages/Historico.jsx`
- `frontend/src/pages/Conversas.jsx`
- `backend/requirements.txt`
- `backend/app.py`
- `backend/api.py`
- `backend/config/settings.py`
- `backend/database/connection.py`
- `backend/database/init_db.py`
- `backend/database/runtime_guards.py`
- `backend/services/bot.py`
- `backend/services/gemini.py`
- `backend/services/whatsapp.py`
- `backend/services/scheduler.py`
- `backend/tests/tests_bot.py`
- `backend/tests/tests_api.py`
- `backend/tests/tests_app.py`
- `teste_bot.py`

### Informações que faltaram no repositório

- não há licença definida
- não há `.env.example` do backend na raiz
- a estratégia oficial de deploy do webhook em ambiente local não está documentada
- a forma pretendida de inicialização do scheduler em produção não está explícita no bootstrap atual
- a finalidade operacional do arquivo `banco de dados/clinica.sql` não está documentada

### Trechos inferidos com segurança a partir do código

- o sistema atende o consultório Paulo Jordão e usa a marca correspondente no frontend
- o painel é servido pelo próprio backend em produção quando `frontend/dist` existe
- o acesso principal ao painel é pela rota `/login`
- o arquivo `backend/assets/Planos 2026.pdf` pode ser servido como fallback do PDF de planos
- o fluxo de pagamento e confirmação depende da ação do profissional no painel, e não de confirmação automática pelo bot
