import os
import sys
from datetime import datetime, timezone

import requests


NOTION_API_URL = "https://api.notion.com/v1/pages/{page_id}"
NOTION_VERSION = "2026-03-11"
GITHUB_API_URL = "https://api.github.com/repos/{repository}"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


def fetch_repository_metadata(repository: str, github_token: str) -> dict:
    response = requests.get(
        GITHUB_API_URL.format(repository=repository),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {github_token}",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def build_notion_properties(repository_data: dict) -> dict:
    repo_url = repository_data["html_url"]
    default_branch = repository_data["default_branch"]
    pushed_at = repository_data.get("pushed_at")

    if not pushed_at:
        pushed_at = datetime.now(timezone.utc).isoformat()

    return {
        "Repositório GitHub": {"url": repo_url},
        "Branches relevantes": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": default_branch},
                }
            ]
        },
        "Issues GitHub": {"url": f"{repo_url}/issues"},
        "Pull requests GitHub": {"url": f"{repo_url}/pulls"},
        "Última atualização GitHub": {
            "date": {"start": pushed_at}
        },
    }


def update_notion_page(notion_token: str, notion_page_id: str, properties: dict) -> None:
    response = requests.patch(
        NOTION_API_URL.format(page_id=notion_page_id),
        headers={
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        json={"properties": properties},
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    try:
        notion_token = require_env("NOTION_TOKEN")
        notion_page_id = require_env("NOTION_PAGE_ID")
        github_token = require_env("GH_TOKEN")
        repository = require_env("GITHUB_REPOSITORY")

        repository_data = fetch_repository_metadata(repository, github_token)
        properties = build_notion_properties(repository_data)
        update_notion_page(notion_token, notion_page_id, properties)

        print("Sincronização GitHub → Notion concluída com sucesso.")
        print(f"Repositório: {repository_data['full_name']}")
        print(f"Branch principal: {repository_data['default_branch']}")
        return 0
    except Exception as exc:
        print(f"Erro na sincronização: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
