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
            CREATE TABLE IF NOT EXISTS consultas (
                id               INT  NOT NULL AUTO_INCREMENT,
                cliente_id       INT  NOT NULL,
                tipo_consulta    ENUM('primeira_consulta', 'retorno') NOT NULL,
                data             DATE NOT NULL,
                horario          TIME NOT NULL,
                status           ENUM('agendada', 'cancelada', 'concluida') NOT NULL DEFAULT 'agendada',
                lembrete_enviado TINYINT(1) NOT NULL DEFAULT 0,
                medico_id        INT  NOT NULL DEFAULT 1,
                PRIMARY KEY (id),
                KEY fk_consultas_cliente (cliente_id),
                KEY fk_consultas_medico  (medico_id),
                CONSTRAINT fk_consultas_cliente
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                CONSTRAINT fk_consultas_medico
                    FOREIGN KEY (medico_id)  REFERENCES medicos (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estados_conversa (
                telefone     VARCHAR(20)  NOT NULL,
                estado       VARCHAR(50)  NOT NULL,
                dados        JSON         DEFAULT NULL,
                atualizado_em TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
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

        # Médico padrão
        cursor.execute("""
            INSERT INTO medicos (id, nome, telefone, ativo)
            VALUES (1, 'Dr. Paulo', '5561900000000', 1)
            ON DUPLICATE KEY UPDATE
                nome     = VALUES(nome),
                telefone = VALUES(telefone),
                ativo    = VALUES(ativo)
        """)

    logger.info("Banco MySQL inicializado com sucesso.")


if __name__ == "__main__":
    init_db()
