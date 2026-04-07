import logging

from database.connection import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id        INT          NOT NULL AUTO_INCREMENT,
                nome      VARCHAR(100) DEFAULT NULL,
                telefone  VARCHAR(20)  NOT NULL,
                sexo      VARCHAR(20)  DEFAULT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY uq_clientes_telefone (telefone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicos (
                id        INT          NOT NULL AUTO_INCREMENT,
                nome      VARCHAR(100) NOT NULL,
                telefone  VARCHAR(20)  NOT NULL,
                ativo     TINYINT(1)   DEFAULT 1,
                PRIMARY KEY (id),
                UNIQUE KEY uq_medicos_telefone (telefone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS planos (
                id                  INT          NOT NULL AUTO_INCREMENT,
                codigo              VARCHAR(50)  NOT NULL,
                nome                VARCHAR(150) NOT NULL,
                valor_total         DECIMAL(10,2) NOT NULL,
                valor_adiantamento  DECIMAL(10,2) NOT NULL,
                ativo               TINYINT(1)   NOT NULL DEFAULT 1,
                PRIMARY KEY (id),
                UNIQUE KEY uq_planos_codigo (codigo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consultas (
                id                  INT  NOT NULL AUTO_INCREMENT,
                cliente_id          INT  NOT NULL,
                plano_id            INT  DEFAULT NULL,
                tipo_consulta       ENUM('primeira_consulta', 'retorno') NOT NULL,
                data                DATE NOT NULL,
                horario             TIME NOT NULL,
                status              ENUM(
                                        'aguardando_pagamento',
                                        'confirmado',
                                        'cancelado',
                                        'concluido'
                                    ) NOT NULL DEFAULT 'aguardando_pagamento',
                pagamento_expira_em DATETIME    DEFAULT NULL,
                lembrete_enviado    TINYINT(1)  NOT NULL DEFAULT 0,
                medico_id           INT  NOT NULL DEFAULT 1,
                PRIMARY KEY (id),
                KEY fk_consultas_cliente (cliente_id),
                KEY fk_consultas_medico  (medico_id),
                KEY fk_consultas_plano   (plano_id),
                CONSTRAINT fk_consultas_cliente
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                CONSTRAINT fk_consultas_medico
                    FOREIGN KEY (medico_id)  REFERENCES medicos (id),
                CONSTRAINT fk_consultas_plano
                    FOREIGN KEY (plano_id)   REFERENCES planos (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estados_conversa (
                telefone      VARCHAR(20)  NOT NULL,
                estado        VARCHAR(50)  NOT NULL,
                dados         JSON         DEFAULT NULL,
                atualizado_em TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (telefone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensagens_whatsapp (
                id               INT          NOT NULL AUTO_INCREMENT,
                consulta_id      INT          DEFAULT NULL,
                telefone_destino VARCHAR(20)  NOT NULL,
                tipo_mensagem    VARCHAR(50)  NOT NULL,
                message_id       VARCHAR(255) DEFAULT NULL,
                status_envio     VARCHAR(50)  NOT NULL DEFAULT 'enviado',
                payload          TEXT,
                resposta_api     TEXT,
                criado_em        TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY fk_mensagens_consulta (consulta_id),
                CONSTRAINT fk_mensagens_consulta
                    FOREIGN KEY (consulta_id) REFERENCES consultas (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_login_attempts (
                identificador   VARCHAR(255) NOT NULL,
                tentativas      INT NOT NULL DEFAULT 0,
                bloqueado_ate   DATETIME DEFAULT NULL,
                atualizado_em   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (identificador)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_dedup (
                message_id      VARCHAR(255) NOT NULL,
                criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Médico padrão
        cursor.execute("""
            INSERT INTO medicos (id, nome, telefone, ativo)
            VALUES (1, 'Dr. Paulo', '5561900000000', 1)
            ON DUPLICATE KEY UPDATE
                nome     = VALUES(nome),
                telefone = VALUES(telefone),
                ativo    = VALUES(ativo)
        """)

        # Planos padrão (valor_adiantamento = 50% do valor_total)
        planos = [
            ("nutri_consulta_unica",      "Consulta Nutricional Completa",                          450.00,  225.00),
            ("nutri_trimestral",          "Pacote Trimestral Premium",                               850.00,  425.00),
            ("nutri_semestral",           "Plano Semestral Alta Performance",                       1600.00,  800.00),
            ("nutri_grupo_1amigo",        "Consulta em Grupo — 1 amigo",                             400.00,  200.00),
            ("nutri_grupo_2amigos",       "Consulta em Grupo — 2 amigos",                            360.00,  180.00),
            ("treino_consulta_unica",     "Consulta Nutricional + Treino Completo",                  620.00,  310.00),
            ("treino_trimestral",         "Pacote Trimestral Nutrição + Treino Premium",            1120.00,  560.00),
            ("treino_semestral",          "Plano Semestral Nutrição + Treino Alta Performance",     2020.00, 1010.00),
            ("treino_grupo_1amigo",       "Consulta + Treino em Grupo — 1 amigo",                   560.00,  280.00),
            ("treino_grupo_2amigos",      "Consulta + Treino em Grupo — 2 amigos",                  500.00,  250.00),
        ]
        for codigo, nome, total, adiant in planos:
            cursor.execute("""
                INSERT INTO planos (codigo, nome, valor_total, valor_adiantamento)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nome               = VALUES(nome),
                    valor_total        = VALUES(valor_total),
                    valor_adiantamento = VALUES(valor_adiantamento)
            """, (codigo, nome, total, adiant))

    logger.info("Banco MySQL inicializado com sucesso.")


if __name__ == "__main__":
    init_db()
