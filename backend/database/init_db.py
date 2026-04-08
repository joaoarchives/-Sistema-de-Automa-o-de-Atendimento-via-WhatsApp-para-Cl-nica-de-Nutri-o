import logging

from config.settings import Config
from database.connection import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (Config.DB_NAME, table_name, column_name),
    )
    return cursor.fetchone() is not None


def _ensure_column(cursor, table_name: str, column_name: str, ddl: str) -> None:
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(ddl)


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
                id                                   INT  NOT NULL AUTO_INCREMENT,
                cliente_id                           INT  NOT NULL,
                plano_id                             INT  DEFAULT NULL,
                tipo_consulta                        ENUM('primeira_consulta', 'retorno') NOT NULL,
                data                                 DATE NOT NULL,
                horario                              TIME NOT NULL,
                status                               ENUM(
                                                        'aguardando_pagamento',
                                                        'confirmado',
                                                        'cancelado',
                                                        'concluido'
                                                    ) NOT NULL DEFAULT 'aguardando_pagamento',
                pagamento_expira_em                  DATETIME    DEFAULT NULL,
                pagamento_confirmado_em              DATETIME    DEFAULT NULL,
                motivo_cancelamento                  TEXT        DEFAULT NULL,
                pagamento_notificacao_em_andamento   TINYINT(1)  NOT NULL DEFAULT 0,
                pagamento_notificacao_lock_em        DATETIME    DEFAULT NULL,
                confirmacao_whatsapp_enviada_em      DATETIME    DEFAULT NULL,
                recomendacoes_whatsapp_enviadas_em   DATETIME    DEFAULT NULL,
                lembrete_enviado                     TINYINT(1)  NOT NULL DEFAULT 0,
                lembrete_24h_enviado                 TINYINT(1)  NOT NULL DEFAULT 0,
                lembrete_12h_enviado                 TINYINT(1)  NOT NULL DEFAULT 0,
                medico_id                            INT  NOT NULL DEFAULT 1,
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

        _ensure_column(cursor, "consultas", "motivo_cancelamento", "ALTER TABLE consultas ADD COLUMN motivo_cancelamento TEXT DEFAULT NULL")
        _ensure_column(cursor, "consultas", "pagamento_confirmado_em", "ALTER TABLE consultas ADD COLUMN pagamento_confirmado_em DATETIME DEFAULT NULL")
        _ensure_column(cursor, "consultas", "pagamento_notificacao_em_andamento", "ALTER TABLE consultas ADD COLUMN pagamento_notificacao_em_andamento TINYINT(1) NOT NULL DEFAULT 0")
        _ensure_column(cursor, "consultas", "pagamento_notificacao_lock_em", "ALTER TABLE consultas ADD COLUMN pagamento_notificacao_lock_em DATETIME DEFAULT NULL")
        _ensure_column(cursor, "consultas", "confirmacao_whatsapp_enviada_em", "ALTER TABLE consultas ADD COLUMN confirmacao_whatsapp_enviada_em DATETIME DEFAULT NULL")
        _ensure_column(cursor, "consultas", "recomendacoes_whatsapp_enviadas_em", "ALTER TABLE consultas ADD COLUMN recomendacoes_whatsapp_enviadas_em DATETIME DEFAULT NULL")
        _ensure_column(cursor, "consultas", "lembrete_24h_enviado", "ALTER TABLE consultas ADD COLUMN lembrete_24h_enviado TINYINT(1) NOT NULL DEFAULT 0")
        _ensure_column(cursor, "consultas", "lembrete_12h_enviado", "ALTER TABLE consultas ADD COLUMN lembrete_12h_enviado TINYINT(1) NOT NULL DEFAULT 0")

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

        cursor.execute("""
            INSERT INTO medicos (id, nome, telefone, ativo)
            VALUES (1, 'Dr. Paulo', '5561900000000', 1)
            ON DUPLICATE KEY UPDATE
                nome     = VALUES(nome),
                telefone = VALUES(telefone),
                ativo    = VALUES(ativo)
        """)

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
