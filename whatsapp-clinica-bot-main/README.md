# 📲 WhatsApp Clínica Bot

> Automação completa de atendimento para clínica de nutrição via WhatsApp — do agendamento ao comprovante, sem intervenção humana.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em_Produção-brightgreen?style=for-the-badge)

---

## 🎯 O que é

Bot de atendimento via WhatsApp que automatiza **100% do processo de agendamento** de uma clínica de nutrição. O paciente envia uma mensagem, o bot conduz a conversa com menus interativos clicáveis, verifica horários disponíveis em tempo real, coleta os dados, confirma o agendamento e notifica o médico — tudo sem nenhuma intervenção humana.

O sistema conta também com um **painel web** exclusivo para o nutricionista visualizar e gerenciar a agenda do dia, da semana e o histórico completo de consultas.

---

## ✨ Funcionalidades

### Bot WhatsApp
- 🗓️ **Agendamento completo** via menus interativos clicáveis
- 🔄 **Diferenciação** entre primeira consulta e retorno
- ⏰ **Controle de horários em tempo real** — bloqueia automaticamente slots ocupados
- 🤖 **IA integrada** (Gemini 2.5 Flash) para responder dúvidas sobre planos e serviços em linguagem natural
- 📅 **Interpretação de datas** em linguagem natural ("quarta-feira", "amanhã", "próxima sexta")
- 📎 **Recebimento de comprovante** de pagamento via imagem/PDF
- ⏳ **Expiração automática** de pagamentos pendentes após 1 hora
- 🔔 **Lembretes automáticos** antes da consulta via APScheduler
- 📋 **Envio automático do PDF** de planos na primeira mensagem
- 💬 **Tratamento inteligente** de agradecimentos e mensagens fora do fluxo
- 🔁 **Deduplicação de mensagens** — evita processamento duplo por retries do WhatsApp

### Painel Web (Nutricionista)
- 🔐 **Login com JWT** — acesso exclusivo para o médico
- 📆 **Agenda do dia** com filtro por data e status
- 📊 **Agenda da semana** agrupada por dia
- 📜 **Histórico completo** de consultas com paginação
- ✅ **Confirmar pagamento**, concluir e cancelar consultas diretamente pelo painel
- 📩 **Notificação ao médico** via WhatsApp ao confirmar novo agendamento
- 📊 **Resumo diário** da agenda enviado ao médico às 06h automaticamente

---

## 🏗️ Arquitetura

```
wppclinica/
├── backend/
│   ├── app.py                          # Webhook Flask + deduplicação de mensagens
│   ├── api.py                          # API REST para o painel web (JWT)
│   ├── config/
│   │   └── settings.py                 # Variáveis de ambiente
│   ├── database/
│   │   ├── connection.py               # Conexão MySQL
│   │   ├── clientes.py                 # CRUD de pacientes
│   │   ├── consultas.py                # CRUD de agendamentos e planos
│   │   ├── estados.py                  # Persistência do estado de conversa
│   │   ├── mensagens.py                # Log de mensagens enviadas
│   │   └── init_db.py                  # Criação de tabelas e seed inicial
│   ├── services/
│   │   ├── bot.py                      # Máquina de estados do fluxo de conversa
│   │   ├── bot_response.py             # Modelo de resposta do bot
│   │   ├── gemini.py                   # Integração com Gemini 2.5 Flash
│   │   ├── whatsapp.py                 # Integração com WhatsApp Cloud API
│   │   ├── agendamento_service.py      # Regras de negócio de agendamento
│   │   ├── scheduler.py                # Lembretes e expiração automática (APScheduler)
│   │   └── notificacoes_medico.py      # Notificações e resumo diário
│   ├── utils/
│   │   └── helpers.py                  # Helpers de data, horário e formatação
│   └── tests/
│       └── tests_bot.py                # Testes unitários do fluxo
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx               # Autenticação do médico
│   │   │   ├── AgendaDia.jsx           # Agenda do dia com filtros
│   │   │   ├── AgendaSemana.jsx        # Agenda semanal agrupada
│   │   │   └── Historico.jsx           # Histórico paginado
│   │   ├── components/
│   │   │   ├── ConsultaCard.jsx        # Card de consulta com ações
│   │   │   └── Layout.jsx              # Layout base com navegação
│   │   └── api/
│   │       └── api.js                  # Chamadas à API REST
│   └── package.json
│
├── teste_bot.py                        # Simulador de conversa no terminal
└── .env.example
```

---

## 💬 Fluxo de Conversa

```
Paciente envia mensagem
        │
        ▼
Bot envia PDF de planos + boas-vindas
        │
        ▼
Gemini detecta intenção (agendar / dúvida / recusar)
        │
        ├── Dúvida → Gemini responde em linguagem natural → volta ao início
        ├── Recusar → encerra atendimento
        │
        └── Agendar
              │
              ▼
        [Lista clicável] Selecionar plano
              │
              ▼
        [Lista clicável] Tipo: Primeira consulta / Retorno
              │
              ▼
        Qual data? (linguagem natural ou DD/MM)
              │
              ▼
        Confirmação da data
              │
              ▼
        [Lista clicável] Período: Manhã / Tarde
              │
              ▼
        [Lista clicável] Horário disponível
              │
              ▼
        Nome completo
              │
              ▼
        [Lista clicável] Sexo
              │
              ▼
        [Lista clicável] Confirmar / Cancelar agendamento
              │
              ▼
        Instruções de pagamento + recomendações pré-consulta
              │
              ▼
        Paciente envia comprovante (imagem/PDF)
              │
              ▼
        Médico recebe notificação → confirma pelo painel
              │
              ▼
        Paciente recebe confirmação ✅
```

---

## 🗄️ Modelo de Dados

```
┌─────────────────────┐       ┌──────────────────────────────────┐
│      clientes       │       │            consultas             │
├─────────────────────┤       ├──────────────────────────────────┤
│ id        INT PK    │◄──────│ cliente_id       INT FK          │
│ nome      VARCHAR   │       │ medico_id        INT FK          │
│ telefone  VARCHAR   │       │ plano_id         INT FK          │
│ sexo      VARCHAR   │       │ tipo_consulta    VARCHAR         │
└─────────────────────┘       │ data             DATE            │
                              │ horario          TIME            │
                              │ status           VARCHAR         │
                              │ pagamento_expira DATETIME        │
                              │ lembrete_enviado TINYINT         │
                              └──────────────────────────────────┘

┌─────────────────────┐       ┌──────────────────────────────────┐
│  estados_conversa   │       │             planos               │
├─────────────────────┤       ├──────────────────────────────────┤
│ telefone  VARCHAR PK│       │ id               INT PK          │
│ estado    VARCHAR   │       │ codigo           VARCHAR UNIQ    │
│ dados     JSON      │       │ nome             VARCHAR         │
└─────────────────────┘       │ valor_total      DECIMAL         │
                              │ valor_adiantamento DECIMAL       │
┌─────────────────────┐       │ ativo            TINYINT         │
│      medicos        │       └──────────────────────────────────┘
├─────────────────────┤
│ id        INT PK    │       ┌──────────────────────────────────┐
│ nome      VARCHAR   │       │       mensagens_whatsapp         │
│ telefone  VARCHAR   │       ├──────────────────────────────────┤
│ ativo     TINYINT   │       │ id               INT PK          │
└─────────────────────┘       │ telefone_destino VARCHAR         │
                              │ tipo_mensagem    VARCHAR         │
                              │ message_id       VARCHAR         │
                              │ status_envio     VARCHAR         │
                              │ payload          JSON            │
                              │ resposta_api     JSON            │
                              │ criado_em        TIMESTAMP       │
                              └──────────────────────────────────┘
```

---

## ⚙️ Stack

| Camada | Tecnologia |
|--------|-----------|
| Bot / Webhook | Python 3.11 + Flask |
| IA | Google Gemini 2.5 Flash |
| Banco de dados | MySQL 8.0 |
| Agendamento de tarefas | APScheduler |
| Mensageria | WhatsApp Cloud API (Meta) |
| Painel web | React 19 + Vite |
| Autenticação | JWT (PyJWT) |
| Exposição local | ngrok |

---

## 🚀 Como rodar

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- MySQL local ou em nuvem
- Conta na [Meta for Developers](https://developers.facebook.com/) com WhatsApp Business API configurada
- Chave da [Google AI Studio](https://aistudio.google.com/) (Gemini)
- [ngrok](https://ngrok.com/) para testes locais

### 1. Clonar o repositório

```bash
git clone https://github.com/joaoarchives/whatsapp-clinica-bot.git
cd whatsapp-clinica-bot
```

### 2. Backend

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv ../.venv
../.venv/Scripts/activate       # Windows
source ../.venv/bin/activate    # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp ../.env.example ../.env
# Edite o .env com suas credenciais
```

### 3. Banco de dados

```sql
CREATE DATABASE clinica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
python database/init_db.py
```

### 4. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

### 5. Rodar o backend

```bash
cd ../backend
python app.py
```

### 6. Expor o webhook com ngrok

```bash
ngrok http 5000
```

Configure a URL gerada (`https://xxxx.ngrok-free.app/webhook`) no painel da Meta como endpoint do webhook.

---

## 🔧 Variáveis de ambiente

```env
# Flask
SECRET_KEY=sua_chave_secreta
FLASK_ENV=development

# WhatsApp Cloud API
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_API_VERSION=v23.0
WEBHOOK_VERIFY_TOKEN=token_de_verificacao_webhook

# Gemini
GEMINI_API_KEY=sua_chave_gemini

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=clinica

# Painel (credenciais do médico)
MEDICO_USER=drpaulo
MEDICO_PASS=senha_segura

# URL do PDF de planos (hospedado externamente)
PDF_PLANOS_URL=https://link-do-seu-pdf.com/Planos_2026.pdf

# URL do frontend (para CORS)
FRONTEND_URL=http://localhost:5173
```

> ⚠️ **Nunca versione o `.env`.** Ele já está no `.gitignore`.

---

## 🧪 Testando localmente

Para simular uma conversa sem precisar do WhatsApp:

```bash
cd backend
python ../teste_bot.py
```

O simulador exibe os menus interativos no terminal e permite testar todo o fluxo de agendamento localmente.

---

## 📁 Planos disponíveis (seed)

| Código | Plano | Valor |
|--------|-------|-------|
| `nutri_consulta_unica` | Consulta Nutricional Completa | R$ 450 |
| `nutri_trimestral` | Pacote Trimestral Premium | R$ 850 |
| `nutri_semestral` | Plano Semestral Alta Performance | R$ 1.600 |
| `nutri_grupo_1amigo` | Consulta em Grupo — 1 amigo | R$ 400/pessoa |
| `nutri_grupo_2amigos` | Consulta em Grupo — 2 amigos | R$ 360/pessoa |
| `treino_consulta_unica` | Consulta + Treino Completo | R$ 620 |
| `treino_trimestral` | Trimestral Nutrição + Treino Premium | R$ 1.120 |
| `treino_semestral` | Semestral Nutrição + Treino Alta Perf. | R$ 2.020 |

---

## 👨‍💻 Autor

**João Victor Mendes Silveira**  
Ciência da Computação — UDF, 5º semestre

[![GitHub](https://img.shields.io/badge/GitHub-joaoarchives-181717?style=for-the-badge&logo=github)](https://github.com/joaoarchives)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-João_Victor-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jo%C3%A3o-victor-m-silveira-478542311)
