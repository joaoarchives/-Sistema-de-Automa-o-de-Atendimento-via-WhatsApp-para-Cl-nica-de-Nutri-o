# 📲 WhatsApp Clinic Bot — Automação de Atendimento para Clínica de Nutrição

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_Cloud_API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=for-the-badge)

**Bot de atendimento via WhatsApp que automatiza agendamentos, lembretes e notificações para clínicas de nutrição — sem intervenção humana.**

</div>

---

## 🎯 O que esse sistema faz

O paciente envia uma mensagem. O bot responde com um menu interativo, coleta as informações necessárias, verifica os horários disponíveis no banco de dados, confirma o agendamento e notifica o médico — tudo automaticamente.

- **Agendamento completo via WhatsApp** — sem ligações, sem formulários
- **Controle de horários em tempo real** — bloqueia automaticamente slots ocupados
- **Lembretes automáticos** antes da consulta via APScheduler
- **Notificação ao médico** ao confirmar novo agendamento
- **Resumo diário da agenda** enviado ao médico às 06h
- **Log completo** de todas as mensagens enviadas pela API

---

## 🏗️ Arquitetura

```
wppclinica/
├── app.py                        # Webhook Flask — recebe e roteia mensagens
├── config/
│   └── settings.py               # Variáveis de ambiente via .env
├── database/
│   ├── connection.py             # Conexão com MySQL
│   ├── clientes.py               # CRUD de pacientes
│   ├── consultas.py              # CRUD de agendamentos
│   ├── estados.py                # Persistência de estado de conversa
│   ├── mensagens.py              # Log de mensagens enviadas
│   └── init_db.py                # Criação das tabelas e seed inicial
├── services/
│   ├── bot.py                    # Lógica do fluxo de conversa
│   ├── whatsapp.py               # Integração com WhatsApp Cloud API
│   ├── scheduler.py              # Lembretes automáticos (APScheduler)
│   └── notificacoes_medico.py    # Notificações e resumo diário
├── utils/
│   └── helpers.py                # Helpers de data, horário e JSON
├── tests/
│   └── tests_bot.py              # Testes unitários
├── clinica.sql                   # Dump do banco de dados
├── .env.example
├── requirements.txt
└── README.md
```

---

## 💬 Fluxo de Conversa

```
[Usuário envia mensagem]
        │
        ▼
[Bot verifica estado atual no banco]
        │
        ├── INICIO / palavras-chave ──► Menu principal
        │                                     │
        │                         ┌───────────┴───────────┐
        │                    [1] Agendar             [2] Cancelar
        │                         │                       │
        │               Tipo de consulta          Cancela a última
        │                         │               consulta agendada
        │              ┌──────────┴──────────┐
        │         [1] Primeira          [2] Retorno
        │              │
        │              ▼
        │       Período (Manhã / Tarde)
        │              │
        │              ▼
        │       Data (DD/MM)
        │              │
        │              ▼
        │       Horários disponíveis
        │              │
        │              ▼
        │       Coleta nome e sexo
        │              │
        │              ▼
        │       Resumo para confirmação
        │              │
        └── Salva no banco ──► Confirmação + notificação ao médico
```

---

## 🗄️ Modelo de Dados

```
┌──────────────────────────────┐         ┌──────────────────────────────────┐
│           clientes           │         │            consultas              │
├──────────────────────────────┤         ├──────────────────────────────────┤
│ id          INT (PK, AI)     │         │ id              INT (PK, AI)     │
│ nome        VARCHAR(30)      │         │ telefone        VARCHAR(20) (FK) │
│ sobrenome   VARCHAR(60)      │◄────────│ tipo_consulta   VARCHAR(30)      │
│ telefone    VARCHAR(20) UNIQ │         │ data            DATE             │
│ sexo        VARCHAR(20)      │         │ horario         TIME             │
└──────────────────────────────┘         │ status          VARCHAR(20)      │
                                         │ lembrete_enviado TINYINT(1)      │
                                         │ medico_id       INT (FK)         │
                                         └──────────────────────────────────┘
                                                          │
                                                          ▼
┌──────────────────────────────┐         ┌──────────────────────────────────┐
│      estados_conversa        │         │              medicos              │
├──────────────────────────────┤         ├──────────────────────────────────┤
│ telefone    VARCHAR(20) (PK) │         │ id         INT (PK, AI)          │
│ estado      VARCHAR(50)      │         │ nome       VARCHAR(100)          │
│ dados       JSON             │         │ telefone   VARCHAR(20)           │
└──────────────────────────────┘         │ ativo      TINYINT(1)            │
                                         └──────────────────────────────────┘

┌────────────────────────────────────────┐
│          mensagens_whatsapp            │
├────────────────────────────────────────┤
│ id                INT (PK, AI)         │
│ consulta_id       INT (FK, nullable)   │
│ telefone_destino  VARCHAR(20)          │
│ tipo_mensagem     VARCHAR(50)          │
│ message_id        VARCHAR(255)         │
│ status_envio      VARCHAR(50)          │
│ payload           TEXT (JSON)          │
│ resposta_api      TEXT (JSON)          │
│ criado_em         TIMESTAMP            │
└────────────────────────────────────────┘
```

---

## ⚙️ Stack

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| Flask | Backend / Webhook |
| MySQL | Banco de dados relacional |
| APScheduler | Lembretes e tarefas agendadas |
| WhatsApp Cloud API (Meta) | Envio e recebimento de mensagens |
| python-dotenv | Gerenciamento de variáveis de ambiente |
| ngrok | Exposição do webhook em desenvolvimento |

---

## 🚀 Como rodar

### Pré-requisitos

- Python 3.11+
- MySQL local ou em nuvem
- Conta na [Meta for Developers](https://developers.facebook.com/) com WhatsApp Business API configurada
- [ngrok](https://ngrok.com/) para testes locais

### 1. Clonar o repositório

```bash
git clone https://github.com/joaoarchives/whatsapp-clinic-bot.git
cd whatsapp-clinic-bot
```

### 2. Ambiente virtual

```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

```env
FLASK_ENV=development
SECRET_KEY=sua_chave_secreta

# WhatsApp Cloud API
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_API_VERSION=v23.0

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=clinica

# Webhook
WEBHOOK_VERIFY_TOKEN=token_de_verificacao_webhook
```

> ⚠️ Nunca versione o `.env`. Ele já está no `.gitignore`.

### 5. Criar o banco e inicializar as tabelas

```sql
CREATE DATABASE clinica CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
python database/init_db.py
```

### 6. Rodar a aplicação

```bash
flask run
```

### 7. Expor o webhook com ngrok

```bash
ngrok http 5000
```

Configure a URL gerada (`https://xxxx.ngrok.io/webhook`) no painel da Meta como endpoint do webhook.

---

## ✅ Funcionalidades

- [x] Menu automático de atendimento
- [x] Escolha de período (manhã / tarde)
- [x] Bloqueio automático de horários ocupados
- [x] Diferenciação entre primeira consulta e retorno
- [x] Coleta de dados do paciente (nome e sexo)
- [x] Confirmação antes de salvar o agendamento
- [x] Cancelamento de consultas via WhatsApp
- [x] Notificação ao médico ao confirmar nova consulta
- [x] Resumo diário da agenda enviado ao médico às 06h
- [x] Log completo de mensagens enviadas
- [ ] Instruções pré-consulta automáticas após agendamento
- [ ] Lembretes configuráveis por tipo de consulta
- [ ] Painel web para o nutricionista visualizar a agenda
- [ ] Integração com LLM para atendimento mais natural

---

## 👨‍💻 Autor

**João Victor Mendes Silveira**
Ciência da Computação — UDF, 5º semestre

[![GitHub](https://img.shields.io/badge/GitHub-joaoarchives-181717?style=for-the-badge&logo=github)](https://github.com/joaoarchives)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-João_Victor-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/joão-victor-m-silveira-478542311)
