"""Read-only connector for public Greenhouse Job Board pages."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
SOURCE = "greenhouse"
BRAZIL_LOCATION = re.compile(
    r"\b(brazil|brasil|sao paulo|são paulo|rio de janeiro|recife|curitiba|"
    r"belo horizonte|porto alegre|florianopolis|florianópolis|bras[ií]lia|"
    r"fortaleza|salvador|manaus|remote\s*[-–—]?\s*(br|brazil|brasil))\b",
    re.IGNORECASE,
)


class GreenhouseAPIError(RuntimeError):
    """Safe Greenhouse API error without request URL or response body."""


def _validate_board_token(token: str) -> str:
    token = token.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise ValueError("Board token inválido.")
    return token


def _fetch_board(
    *, board_token: str, include_content: bool, timeout: float
) -> dict[str, Any]:
    query = urlencode({"content": "true"}) if include_content else ""
    url = f"{API_BASE_URL}/{board_token}/jobs"
    if query:
        url = f"{url}?{query}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Data-AI-Job-Market-Intelligence/2.0 (educational research)",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise GreenhouseAPIError(f"Greenhouse respondeu com HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise GreenhouseAPIError("Não foi possível conectar à Greenhouse.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise GreenhouseAPIError("A resposta Greenhouse não contém JSON válido.") from None

    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise GreenhouseAPIError("Resposta Greenhouse sem a lista 'jobs'.")
    if any(not isinstance(job, dict) for job in payload["jobs"]):
        raise GreenhouseAPIError("Resposta Greenhouse contém vaga em formato inválido.")
    return payload


def is_brazil_compatible(job: dict[str, Any]) -> bool:
    """Match explicit Brazil locations; a generic 'Remote' is insufficient."""
    location = (job.get("location") or {}).get("name", "")
    office_locations = [
        office.get("location", "")
        for office in job.get("offices", [])
        if isinstance(office, dict)
    ]
    text = " ".join([str(location), *map(str, office_locations)])
    return bool(BRAZIL_LOCATION.search(text))


def extract_board_jobs(
    *,
    board_token: str,
    include_content: bool = False,
    brazil_only: bool = True,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Fetch one company's published job list and retain the raw API payload."""
    token = _validate_board_token(board_token)
    if not isinstance(brazil_only, bool) or not isinstance(include_content, bool):
        raise ValueError("brazil_only e include_content devem ser booleanos.")

    payload = _fetch_board(
        board_token=token, include_content=include_content, timeout=timeout
    )
    jobs = payload["jobs"]
    selected = (
        [job for job in jobs if is_brazil_compatible(job)] if brazil_only else jobs
    )
    return {
        "source": SOURCE,
        "source_url": f"https://boards.greenhouse.io/{token}",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "board_token": token,
            "include_content": include_content,
            "brazil_only": brazil_only,
        },
        "jobs": selected,
        "raw_response": payload,
        "result_count": len(selected),
        "board_result_count": len(jobs),
    }


def extract_configured_boards(
    *,
    board_tokens: list[str],
    include_content: bool = False,
    brazil_only: bool = True,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch selected boards sequentially; errors are surfaced per caller."""
    if not board_tokens:
        raise ValueError("Configure pelo menos um board token.")
    return [
        extract_board_jobs(
            board_token=token,
            include_content=include_content,
            brazil_only=brazil_only,
            timeout=timeout,
        )
        for token in board_tokens
    ]


def write_raw_extraction(extraction: dict[str, Any], output_path: str) -> None:
    """Write a private snapshot only after storage terms have been reviewed."""
    from pathlib import Path

    if extraction.get("source") != SOURCE:
        raise ValueError("O envelope não pertence à fonte Greenhouse.")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
