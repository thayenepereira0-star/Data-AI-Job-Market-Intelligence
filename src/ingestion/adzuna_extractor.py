"""Extração paginada de anúncios brutos pela API pública de busca da Adzuna."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import adzuna_credentials

API_BASE_URL = "https://api.adzuna.com/v1/api"
SUPPORTED_COUNTRIES = {
    "at", "au", "be", "br", "ca", "ch", "de", "es", "fr",
    "gb", "in", "it", "mx", "nl", "nz", "pl", "sg", "us", "za",
}


class AdzunaAPIError(RuntimeError):
    """Erro seguro da API, sem incluir URL ou credenciais na mensagem."""


def _validate_search(
    what: str,
    country: str,
    first_page: int,
    pages: int,
    results_per_page: int,
) -> None:
    if not what.strip():
        raise ValueError("Informe pelo menos um termo em what.")
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"Código de país não suportado: {country}.")
    if first_page < 1:
        raise ValueError("first_page deve ser maior ou igual a 1.")
    if pages < 1:
        raise ValueError("pages deve ser maior ou igual a 1.")
    if results_per_page < 1:
        raise ValueError("results_per_page deve ser maior ou igual a 1.")


def _fetch_page(
    *,
    country: str,
    page: int,
    what: str,
    where: str | None,
    results_per_page: int,
    app_id: str,
    app_key: str,
    timeout: float,
) -> dict[str, Any]:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": what.strip(),
        "content-type": "application/json",
    }
    if where and where.strip():
        params["where"] = where.strip()

    url = f"{API_BASE_URL}/jobs/{country}/search/{page}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        raise AdzunaAPIError(f"A Adzuna respondeu com HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise AdzunaAPIError("Não foi possível conectar à API da Adzuna.") from None

    try:
        import json

        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise AdzunaAPIError("A resposta da Adzuna não contém JSON válido.") from None

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise AdzunaAPIError("A resposta da Adzuna não contém uma lista de resultados.")
    if any(not isinstance(item, dict) for item in data["results"]):
        raise AdzunaAPIError("A resposta da Adzuna contém um anúncio em formato inválido.")
    return data


def extract_jobs(
    *,
    what: str,
    where: str | None = None,
    country: str = "br",
    first_page: int = 1,
    pages: int = 1,
    results_per_page: int = 20,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Busca páginas e devolve metadados junto às respostas originais da API.

    O retorno mantém cada página intacta para que a camada de transformação
    possa tratar os campos e formatos específicos do provedor separadamente.
    """
    _validate_search(what, country, first_page, pages, results_per_page)
    app_id, app_key = adzuna_credentials()

    raw_pages: list[dict[str, Any]] = []
    for page in range(first_page, first_page + pages):
        payload = _fetch_page(
            country=country,
            page=page,
            what=what,
            where=where,
            results_per_page=results_per_page,
            app_id=app_id,
            app_key=app_key,
            timeout=timeout,
        )
        raw_pages.append(payload)
        if not payload["results"]:
            break

    return {
        "source": "adzuna",
        "country": country,
        "query": {
            "what": what.strip(),
            "where": where.strip() if where and where.strip() else None,
            "first_page": first_page,
            "pages_requested": pages,
            "results_per_page": results_per_page,
        },
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "pages": raw_pages,
    }


def write_raw_extraction(extraction: dict[str, Any], output_path: str) -> None:
    """Grava o envelope bruto em JSON UTF-8 sem incluir credenciais."""
    import json
    from pathlib import Path

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
