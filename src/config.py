"""Configuração centralizada para execução local.

Segredos vivem em variáveis de ambiente / .env (ignorado pelo Git).
Nunca imprima os dicionários de credenciais em logs.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv


def _load_environment() -> None:
    # Não substitui variáveis já fornecidas pelo ambiente da execução.
    load_dotenv(override=False)


def connection_settings() -> dict[str, str | int]:
    """Configuração psycopg; falhas não expõem a senha."""
    _load_environment()
    password = os.getenv("POSTGRES_PASSWORD", "").strip()
    if not password or password == "troque-por-uma-senha-local-forte":
        raise ValueError("Defina POSTGRES_PASSWORD no arquivo .env local.")
    raw_port = os.getenv("POSTGRES_PORT", "5432")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("POSTGRES_PORT deve ser um número válido.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT deve estar entre 1 e 65535.")
    values = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "dbname": os.getenv("POSTGRES_DB", "jobmarket"),
        "user": os.getenv("POSTGRES_USER", "jobmarket"),
    }
    if not all(str(value).strip() for value in values.values()):
        raise ValueError("POSTGRES_HOST, POSTGRES_DB e POSTGRES_USER não podem ser vazios.")
    return {**values, "port": port, "password": password, "connect_timeout": 5}


def adzuna_credentials() -> tuple[str, str]:
    """Obtém credenciais opcionais, necessárias somente na futura coleta via API."""
    _load_environment()
    app_id = os.getenv("ADZUNA_APP_ID", "").strip()
    app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key or app_id == "seu_app_id" or app_key == "sua_app_key":
        raise ValueError("Configure ADZUNA_APP_ID e ADZUNA_APP_KEY no .env local.")
    return app_id, app_key
