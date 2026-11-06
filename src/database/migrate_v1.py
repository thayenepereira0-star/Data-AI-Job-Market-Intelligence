"""DAI-26: orquestrador ETL da migração v1 → PostgreSQL.

O comando padrão só faz prévia. --apply grava os registros.
Mantém a interface da DAI-23, agora separada em módulos testáveis.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import psycopg

from src.ingestion.csv_reader import read_csv
from src.processing.job_transform import unique_records
from src.database.job_loader import apply

DEFAULT_CSV = Path("data/processed/jobs_analysis.csv")


