# 📲 Sistema de Automação de Atendimento via WhatsApp para Clínica de Nutrição

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow?style=for-the-badge)

</div>

---

## 📌 Descrição

Projeto em desenvolvimento com o objetivo de automatizar o atendimento de uma clínica de nutrição através da **WhatsApp Business Cloud API (Meta)**.

O sistema é responsável por:

- 🤖 Atendimento automático via chatbot com máquina de estados
- 📅 Agendamento de consultas (primeira consulta ou retorno)
- 🕐 Controle de agenda por período (manhã/tarde) com slots de 30 minutos
- 🔔 Lembretes automáticos de consulta via APScheduler
- 👨‍⚕️ Notificações ao médico sobre novas consultas e resumo diário às 6h
- 📋 Log completo de mensagens enviadas via WhatsApp
- ❌ Cancelamento de consultas pelo próprio paciente

> 💡 Projeto desenvolvido como aplicação prática de estudos em **Python**, **Banco de Dados** e **Backend**.

---

## 🏗️ Estrutura do Projeto

```
wppclinica/
├── app.py                          # Webhook Flask (recebe/responde mensagens)
├── config/
│   └── settings.py                 # Configurações via variáveis de ambiente
├── database/
│   ├── init_db.py                  # Criação das tabelas MySQL
│   ├── connection.py               # Conexão com o banco
│   ├── clientes.py                 # CRUD de clientes/pacientes
│   ├── consultas.py                # Agendamento, cancelamento e verificação de horários
│   └── mensagens.py                # Log de mensagens WhatsApp enviadas
├── services/
│   ├── bot.py                      # Lógica do chatbot (máquina de estados)
│   ├── whatsapp.py                 # Integração com a WhatsApp Cloud API
│   ├── scheduler.py                # Lembretes automáticos com APScheduler
│   └── notificacoes_medico.py      # Resumo diário e alertas ao médico
├── utils/
│   └── helpers.py                  # Funções auxiliares (datas, horários, JSON)
├── tests/
│   └── tests_bot.py
├── .env.example                    # Exemplo de variáveis de ambiente
├── requirements.txt
└── README.md
```

---

## 🗄️ Banco de Dados (MySQL)

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   clientes   │     │    consultas     │     │  mensagens_whatsapp  │
├──────────────┤     ├──────────────────┤     ├──────────────────────┤
│ id (PK)      │◄────│ id (PK)          │────►│ id (PK)              │
│ telefone     │     │ telefone (FK)    │     │ consulta_id (FK)     │
│ nome         │     │ tipo_consulta    │     │ telefone_destino     │
│ sobrenome    │     │ data             │     │ tipo_mensagem        │
│ sexo         │     │ horario          │     │ message_id           │
└──────────────┘     │ status           │     │ status_envio         │
                     │ medico_id (FK)   │     │ payload (JSON)       │
┌──────────────┐     │ lembrete_enviado │     │ resposta_api (JSON)  │
│   medicos    │◄────┤                  │     │ criado_em            │
├──────────────┤     └──────────────────┘     └──────────────────────┘
│ id (PK)      │
│ nome         │     ┌────────────────────┐
│ telefone     │     │  estados_conversa  │
│ ativo        │     ├────────────────────┤
└──────────────┘     │ telefone (PK)      │
                     │ estado             │
                     │ dados (JSON)       │
                     └────────────────────┘
```

---

## 💬 Fluxo de Conversa

```
[Usuário envia mensagem]
        │
        ▼
[Verifica estado no banco]
        │
   ┌────┴────┐
   │  inicio │──► Exibe menu principal
   └────┬────┘
        │
   ┌────┴────┐
   │  menu   │──► 1: Agendar  │  2: Cancelar
   └────┬────┘
        │ (1)
        ▼
  tipo_consulta ──► 1: Primeira consulta  │  2: Retorno
        │
        ▼
   periodo ──► 1: Manhã  │  2: Tarde
        │
        ▼
   data ──► DD/MM (valida e busca horários disponíveis)
        │
        ▼
   horario ──► Lista numerada de slots disponíveis
        │
        ▼
   nome ──► Digita o nome
        │
        ▼
   sexo ──► 1: Masculino  │  2: Feminino  │  3: Outro
        │
        ▼
   confirmacao ──► 1: Confirmar  │  2: Cancelar
        │
        ▼
   Salva consulta → Notifica médico → Retorna ao menu
```

---

## ⚙️ Tecnologias Utilizadas

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| Flask | Servidor web / Webhook |
| MySQL | Banco de dados |
| APScheduler | Lembretes e resumo diário automatizados |
| WhatsApp Cloud API (Meta) | Envio e recebimento de mensagens |
| python-dotenv | Gerenciamento de variáveis de ambiente |
| ngrok | Exposição do webhook em desenvolvimento |

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

- Python 3.11+
- MySQL rodando localmente ou em nuvem
- Conta na [Meta for Developers](https://developers.facebook.com/) com WhatsApp Business API configurada
- [ngrok](https://ngrok.com/) (para testes locais)

### 1. Clonar o repositório

```bash
git clone https://github.com/joaoarchives/wppclinica.git
cd wppclinica
```

### 2. Criar e ativar ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais reais.

### 5. Inicializar o banco de dados

```bash
python database/init_db.py
```

> O script já insere um médico padrão na tabela `medicos`. Edite os dados do médico diretamente no `init_db.py` antes de rodar, ou atualize via SQL após.

### 6. Rodar a aplicação

```bash
python app.py
```

### 7. Expor o webhook com ngrok (desenvolvimento)

```bash
ngrok http 5000
```

Copie a URL gerada (ex: `https://xxxx.ngrok.io`) e configure como webhook no painel da Meta.

---

## ✅ Funcionalidades Implementadas

- [x] Menu automático de atendimento
- [x] Agendamento com escolha de tipo, período, data e horário
- [x] Bloqueio de horários já ocupados
- [x] Diferenciação entre primeira consulta e retorno
- [x] Cancelamento de consulta pelo paciente
- [x] Notificação ao médico quando nova consulta é agendada para o dia
- [x] Resumo diário ao médico às 06h via APScheduler
- [x] Lembretes automáticos de consulta
- [x] Log completo de mensagens enviadas
- [x] Rastreamento de status das mensagens via webhook

## 🔜 Funcionalidades Planejadas

- [ ] Envio de instruções pré-consulta
- [ ] Suporte a múltiplos médicos com agenda independente
- [ ] Painel web para o nutricionista visualizar a agenda

---

## 👨‍💻 Autor

**João Victor Mendes Silveira**  
Bacharelado em Ciência da Computação – UDF

[![GitHub](https://img.shields.io/badge/GitHub-joaoarchives-181717?style=for-the-badge&logo=github)](https://github.com/joaoarchives)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-João_Victor-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/joão-victor-m-silveira-478542311)
