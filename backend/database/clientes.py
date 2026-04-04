from database.connection import get_db


def registrar_cliente_se_nao_existir(telefone: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM clientes WHERE telefone = %s",
            (telefone,),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO clientes (telefone) VALUES (%s)",
                (telefone,),
            )


def atualizar_cliente(telefone: str, nome: str, sexo: str | None = None) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE clientes
            SET nome = %s,
                sexo = %s
            WHERE telefone = %s
            """,
            (nome, sexo, telefone),
        )
