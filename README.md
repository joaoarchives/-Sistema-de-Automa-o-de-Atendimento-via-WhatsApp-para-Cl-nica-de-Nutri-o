# 📲 Sistema de Automação de Atendimento via WhatsApp para Clínica de Nutrição

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=for-the-badge)

</div>

---

## 📌 Descrição

Projeto em desenvolvimento com o objetivo de automatizar o atendimento de uma clínica de nutrição através do **WhatsApp Business API**.

O sistema é responsável por:

- 🤖 Atendimento automático inicial
- 📅 Agendamento de consultas
- 🕐 Controle de agenda com horários fixos
- 📋 Envio automático de instruções pré-consulta
- 🔔 Disparo de lembretes 12h antes da consulta
- ✅ Confirmação e organização da agenda do nutricionista

> 💡 Este projeto está sendo desenvolvido como aplicação prática de estudos em **Python**, **Banco de Dados** e **Backend**.

---

## 🎯 Objetivo do Projeto

Criar um sistema escalável de automação que possa futuramente atender:

- Clínicas de nutrição
- Personal trainers
- Clínicas odontológicas
- Profissionais autônomos
- Pequenas empresas

O sistema será estruturado para permitir **adaptação a diferentes tipos de serviços**.

---

## 🏗️ Estrutura do Projeto

```
whatsapp-clinica/
├── app/
│   ├── __init__.py
│   ├── webhook.py          # Recebimento de mensagens da API Meta
│   ├── bot.py              # Lógica principal do bot e fluxo de conversa
│   ├── scheduler.py        # Agendamento de lembretes automáticos
│   └── utils.py            # Funções auxiliares
├── database/
│   ├── models.py           # Modelos do banco de dados
│   └── db.py               # Conexão e operações com o banco
├── config/
│   └── settings.py         # Variáveis de configuração
├── tests/
│   └── test_bot.py         # Testes unitários
├── .env.example            # Exemplo de variáveis de ambiente
├── requirements.txt
└── README.md
```

| Arquivo | Descrição |
|---|---|
| `webhook.py` | Recebe e valida as mensagens da WhatsApp Cloud API |
| `bot.py` | Controla o estado da conversa e a lógica de agendamento |
| `scheduler.py` | Dispara lembretes automáticos com APScheduler |
| `models.py` | Modelos de Cliente e Consulta no banco de dados |
| `settings.py` | Centraliza configurações e variáveis de ambiente |

---

## 🗄️ Modelo do Banco de Dados

```
┌──────────────────────────┐         ┌──────────────────────────────┐
│         clientes         │         │          consultas            │
├──────────────────────────┤         ├──────────────────────────────┤
│ id          INTEGER (PK) │◄────────│ id            INTEGER (PK)   │
│ nome        TEXT         │         │ cliente_id    INTEGER (FK)   │
│ telefone    TEXT UNIQUE  │         │ data_hora     DATETIME       │
│ tipo        TEXT         │         │ tipo          TEXT           │
│ criado_em   DATETIME     │         │ status        TEXT           │
└──────────────────────────┘         │ lembrete_env  BOOLEAN        │
                                     │ criado_em     DATETIME       │
                                     └──────────────────────────────┘

┌──────────────────────────┐
│     estados_conversa     │
├──────────────────────────┤
│ telefone    TEXT (PK)    │
│ estado      TEXT         │
│ dados_tmp   TEXT (JSON)  │
│ atualizado  DATETIME     │
└──────────────────────────┘
```

| Tabela | Descrição |
|---|---|
| `clientes` | Dados dos pacientes (nome, telefone, tipo: primeira consulta ou retorno) |
| `consultas` | Agendamentos com data/hora, status e controle de lembrete enviado |
| `estados_conversa` | Persiste em qual etapa do fluxo cada usuário está |

---

## 💬 Fluxo de Conversa

```
[Usuário envia mensagem]
        │
        ▼
[Bot verifica estado atual]
        │
        ├── INICIO ──────► Envia menu principal
        │                        │
        │              ┌─────────┴──────────┐
        │              │                    │
        │         [1] Agendar          [2] Cancelar
        │              │                    │
        │     Pergunta tipo de         Busca consultas
        │     consulta                 do cliente
        │              │
        │    ┌──────────┴──────────┐
        │    │                     │
        │ [1] Primeira         [2] Retorno
        │ consulta
        │    │
        │    ▼
        │ Pergunta período (Manhã / Tarde)
        │    │
        │    ▼
        │ Exibe horários disponíveis
        │    │
        │    ▼
        │ Usuário escolhe horário
        │    │
        │    ▼
        │ Confirma agendamento
        │    │
        │    ▼
        └── Salva no banco ──► Envia confirmação + instruções pré-consulta
```

---

## ⚙️ Tecnologias Utilizadas

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| Flask | Backend / Webhook |
| SQLite | Banco de dados (MVP) |
| APScheduler | Agendamento de lembretes |
| WhatsApp Cloud API (Meta) | Envio e recebimento de mensagens |
| python-dotenv | Gerenciamento de variáveis de ambiente |
| ngrok | Exposição do webhook local (desenvolvimento) |

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

- Python 3.11+
- Conta na [Meta for Developers](https://developers.facebook.com/) com WhatsApp Business API configurada
- [ngrok](https://ngrok.com/) instalado (para testes locais)

### 1. Clonar o repositório

```bash
git clone https://github.com/joaoarchives/-Sistema-de-Automa-o-de-Atendimento-via-WhatsApp-para-Cl-nica-de-Nutri-o.git
cd whatsapp-clinica
```

### 2. Criar e ativar ambiente virtual

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env`:

```env
WHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_ID=seu_phone_id_aqui
VERIFY_TOKEN=token_de_verificacao_webhook
DATABASE_URL=sqlite:///clinica.db
```

### 5. Inicializar o banco de dados

```bash
python database/init_db.py
```

### 6. Rodar a aplicação

```bash
flask run
```

### 7. Expor o webhook com ngrok (desenvolvimento)

```bash
ngrok http 5000
```

Copie a URL gerada (ex: `https://xxxx.ngrok.io`) e configure como webhook no painel da Meta.

---

## 🧠 Funcionalidades Planejadas

- [x] Estrutura base do projeto
- [x] Menu automático de atendimento
- [x] Escolha de período (manhã / tarde)
- [ ] Bloqueio automático de horários ocupados
- [ ] Diferenciação entre primeira consulta e retorno
- [ ] Envio de instruções pré-consulta
- [ ] Sistema de lembretes automáticos (12h antes)
- [ ] Cancelamento de consultas via WhatsApp
- [ ] Painel simples para o nutricionista ver a agenda

---

## 📅 Status do Projeto

🚧 **Em desenvolvimento**

Etapas atuais:
- Estruturação da lógica de horários
- Estudo e implementação de geração de slots
- Modelagem do banco de dados

---

## 📚 Aprendizados Envolvidos

Este projeto está sendo desenvolvido para consolidar conhecimentos em:

- Lógica de programação
- Estruturas de repetição
- Manipulação de datas e horários
- Modelagem de banco de dados
- Desenvolvimento de APIs
- Integração com serviços externos

---

## 👨‍💻 Autor

**João Victor Mendes Silveira**  
Bacharelado em Ciência da Computação – UDF  

[![GitHub](https://img.shields.io/badge/GitHub-joaoarchives-181717?style=for-the-badge&logo=github)](https://github.com/joaoarchives)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-João_Victor-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/joão-victor-m-silveira-478542311)
