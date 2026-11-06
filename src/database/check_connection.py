"""DAI-22: verifica conexão Python -> PostgreSQL sem alterar dados.

Uso, na raiz do projeto:
    python -m src.database.check_connection
"""

from __future__ import annotations

import sys

import psycopg

from src.config import connection_settings


def check_connection() -> tuple[str, str, int]:
    """Realiza consulta de leitura e devolve nome do banco, usuário e total de tabelas."""
    settings = connection_settings()
    with psycopg.connect(**settings) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT current_database(), current_user,
                       (SELECT count(*) FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_type = 'BASE TABLE')
                """
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("A consulta de verificação não retornou dados.")
            database, user, table_count = row
            return str(database), str(user), int(table_count)


def main() -> int:
    try:
        database, user, table_count = check_connection()
    except (ValueError, psycopg.Error, OSError) as exc:
        # Não imprimir exceções de driver: podem incluir detalhes de conexão sensíveis.
        print(
            "Falha na conexão. Confira Docker, porta, POSTGRES_USER, "
            "POSTGRES_DB e a senha no .env. "
            f"Tipo do erro: {type(exc).__name__}.",
            file=sys.stderr,
        )
        return 1

    print(f"Conexão OK! Banco: {database}; usuário: {user}; tabelas public: {table_count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
