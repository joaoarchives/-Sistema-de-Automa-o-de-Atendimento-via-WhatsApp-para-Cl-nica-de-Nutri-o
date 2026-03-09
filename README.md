📲 Sistema de Automação de Atendimento via WhatsApp para Clínica de Nutrição
📌 Descrição
Projeto em desenvolvimento com o objetivo de automatizar o atendimento de uma clínica de nutrição através do WhatsApp Business API.
O sistema será responsável por:

Atendimento automático inicial
Agendamento de consultas
Controle de agenda com horários fixos
Envio automático de instruções pré-consulta
Disparo de lembretes 12h antes da consulta
Confirmação e organização da agenda do nutricionista

Este projeto está sendo desenvolvido como aplicação prática de estudos em Python, Banco de Dados e Backend.

🎯 Objetivo do Projeto
Criar um sistema escalável de automação que possa futuramente atender:

Clínicas de nutrição
Personal trainers
Clínicas odontológicas
Profissionais autônomos
Pequenas empresas

O sistema será estruturado para permitir adaptação a diferentes tipos de serviços.

🏗️ Estrutura do Projeto
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
O sistema é dividido nos seguintes módulos:

webhook.py — Recebe e valida as mensagens da WhatsApp Cloud API
bot.py — Controla o estado da conversa e a lógica de agendamento
scheduler.py — Dispara lembretes automáticos com APScheduler
models.py — Modelos de Cliente e Consulta no banco de dados
settings.py — Centraliza configurações e variáveis de ambiente


🗄️ Modelo do Banco de Dados
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
Tabelas:

clientes — Dados dos pacientes (nome, telefone, tipo: primeira consulta ou retorno)
consultas — Agendamentos com data/hora, status e controle de lembrete enviado
estados_conversa — Persiste em qual etapa do fluxo cada usuário está


💬 Fluxo de Conversa
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

⚙️ Tecnologias Utilizadas
TecnologiaUsoPython 3.11+Linguagem principalFlaskBackend / WebhookSQLiteBanco de dados (MVP)APSchedulerAgendamento de lembretesWhatsApp Cloud API (Meta)Envio e recebimento de mensagenspython-dotenvGerenciamento de variáveis de ambientengrokExposição do webhook local (desenvolvimento)

🚀 Como Rodar o Projeto
Pré-requisitos

Python 3.11+
Conta na Meta for Developers com WhatsApp Business API configurada
ngrok instalado (para testes locais)

1. Clonar o repositório
bashgit clone https://github.com/seu-usuario/whatsapp-clinica.git
cd whatsapp-clinica
2. Criar e ativar ambiente virtual
bashpython -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
3. Instalar dependências
bashpip install -r requirements.txt
4. Configurar variáveis de ambiente
Copie o arquivo de exemplo e preencha com suas credenciais:
bashcp .env.example .env
Edite o .env:
envWHATSAPP_TOKEN=seu_token_aqui
WHATSAPP_PHONE_ID=seu_phone_id_aqui
VERIFY_TOKEN=token_de_verificacao_webhook
DATABASE_URL=sqlite:///clinica.db
5. Inicializar o banco de dados
bashpython database/init_db.py
6. Rodar a aplicação
bashflask run
7. Expor o webhook com ngrok (desenvolvimento)
bashngrok http 5000
Copie a URL gerada (ex: https://xxxx.ngrok.io) e configure como webhook no painel da Meta.

🧠 Funcionalidades Planejadas

 Estrutura base do projeto
 Menu automático de atendimento
 Escolha de período (manhã / tarde)
 Bloqueio automático de horários ocupados
 Diferenciação entre primeira consulta e retorno
 Envio de instruções pré-consulta
 Sistema de lembretes automáticos (12h antes)
 Cancelamento de consultas via WhatsApp
 Painel simples para o nutricionista ver a agenda


📅 Status do Projeto
🚧 Em desenvolvimento
Etapas atuais:

Estruturação da lógica de horários
Estudo e implementação de geração de slots
Modelagem do banco de dados


📚 Aprendizados Envolvidos
Este projeto está sendo desenvolvido para consolidar conhecimentos em:

Lógica de programação
Estruturas de repetição
Manipulação de datas e horários
Modelagem de banco de dados
Desenvolvimento de APIs
Integração com serviços externos


👨‍💻 Autor
João Victor Mendes Silveira
Bacharelado em Ciência da Computação – UDF
Projeto pessoal com aplicação real em clínica.
