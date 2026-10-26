import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


NOTION_API_URL = "https://api.notion.com/v1/pages/{page_id}"
NOTION_DATA_SOURCE_QUERY_URL = "https://api.notion.com/v1/data_sources/{data_source_id}/query"
NOTION_VERSION = "2026-03-11"
GITHUB_API_URL = "https://api.github.com/repos/{repository}"
ISSUE_REFERENCE_PATTERN = re.compile(r"(?<![\w/])#(\d+)\b")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return value


def github_headers(github_token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def notion_headers(notion_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def fetch_repository_metadata(repository: str, github_token: str) -> dict[str, Any]:
    response = requests.get(
        GITHUB_API_URL.format(repository=repository),
        headers=github_headers(github_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_latest_commit(
    repository: str, github_token: str, branch: str
) -> dict[str, str] | None:
    response = requests.get(
        f"{GITHUB_API_URL.format(repository=repository)}/commits",
        headers=github_headers(github_token),
        params={"sha": branch, "per_page": 1},
        timeout=30,
    )
    response.raise_for_status()
    commits = response.json()
    if not commits:
        return None

    latest = commits[0]
    commit_data = latest.get("commit", {})
    author_data = commit_data.get("author", {})
    return {
        "message": first_line(commit_data.get("message")),
        "branch": branch,
        "timestamp": author_data.get("date"),
        "sha": latest.get("sha", ""),
    }


def read_event_payload(event_path: str | None) -> dict[str, Any]:
    if not event_path:
        return {}

    path = Path(event_path)
    if not path.is_file():
        return {}

    with path.open(encoding="utf-8") as event_file:
        return json.load(event_file)


def first_line(message: str | None) -> str:
    if not message:
        return ""
    return message.strip().splitlines()[0][:2000]


def branch_from_ref(ref: str | None) -> str:
    if not ref:
        return ""
    prefix = "refs/heads/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def extract_issue_references(message: str | None) -> list[int]:
    if not message:
        return []
    return sorted({int(match) for match in ISSUE_REFERENCE_PATTERN.findall(message)})


def push_activity(payload: dict[str, Any]) -> dict[str, str] | None:
    head_commit = payload.get("head_commit") or {}
    message = first_line(head_commit.get("message"))
    if not message:
        return None

    return {
        "message": message,
        "branch": branch_from_ref(payload.get("ref")),
        "timestamp": head_commit.get("timestamp") or "",
        "sha": head_commit.get("id") or "",
    }


def find_notion_project_page(
    notion_token: str, data_source_id: str, repository_url: str
) -> str:
    response = requests.post(
        NOTION_DATA_SOURCE_QUERY_URL.format(data_source_id=data_source_id),
        headers=notion_headers(notion_token),
        json={
            "filter": {
                "and": [
                    {
                        "property": "Repositório GitHub",
                        "url": {"equals": repository_url},
                    },
                    {
                        "property": "Automação ativa",
                        "checkbox": {"equals": True},
                    },
                ]
            },
            "page_size": 2,
        },
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        raise RuntimeError(
            "Nenhum projeto ativo no Notion corresponde ao repositório "
            f"{repository_url}. Cadastre o repositório na base Projetos GitHub "
            "e marque Automação ativa."
        )

    if len(results) > 1:
        raise RuntimeError(
            "Mais de um projeto ativo no Notion usa o mesmo repositório. "
            "Deixe Automação ativa marcada em apenas um projeto."
        )

    return results[0]["id"]


def rich_text_property(value: str) -> dict[str, Any]:
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": value[:2000]},
            }
        ]
    }


def build_notion_properties(
    repository_data: dict[str, Any], activity: dict[str, str] | None = None
) -> dict[str, Any]:
    repo_url = repository_data["html_url"]
    default_branch = repository_data["default_branch"]
    pushed_at = repository_data.get("pushed_at")

    if activity and activity.get("timestamp"):
        pushed_at = activity["timestamp"]
    if not pushed_at:
        pushed_at = datetime.now(timezone.utc).isoformat()

    properties: dict[str, Any] = {
        "Repositório GitHub": {"url": repo_url},
        "Branches relevantes": rich_text_property(default_branch),
        "Issues GitHub": {"url": f"{repo_url}/issues"},
        "Pull requests GitHub": {"url": f"{repo_url}/pulls"},
        "Última atualização GitHub": {"date": {"start": pushed_at}},
    }

    if activity and activity.get("message"):
        properties["Última atividade"] = rich_text_property(activity["message"])
        properties["Branch da última atividade"] = rich_text_property(
            activity.get("branch") or default_branch
        )

    return properties


def update_notion_page(
    notion_token: str, notion_page_id: str, properties: dict[str, Any]
) -> None:
    response = requests.patch(
        NOTION_API_URL.format(page_id=notion_page_id),
        headers=notion_headers(notion_token),
        json={"properties": properties},
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    try:
        notion_token = require_env("NOTION_TOKEN")
        notion_projects_data_source_id = require_env("NOTION_PROJECTS_DATA_SOURCE_ID")
        github_token = require_env("GH_TOKEN")
        repository = require_env("GITHUB_REPOSITORY")
        event_name = os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch")
        event_payload = read_event_payload(os.getenv("GITHUB_EVENT_PATH"))

        repository_data = fetch_repository_metadata(repository, github_token)
        notion_page_id = find_notion_project_page(
            notion_token,
            notion_projects_data_source_id,
            repository_data["html_url"],
        )

        activity = None
        if event_name == "push":
            activity = push_activity(event_payload)
        elif event_name == "workflow_dispatch":
            activity = fetch_latest_commit(
                repository,
                github_token,
                repository_data["default_branch"],
            )

        properties = build_notion_properties(repository_data, activity)
        update_notion_page(notion_token, notion_page_id, properties)

        print("Sincronização GitHub → Notion concluída com sucesso.")
        print(f"Evento: {event_name}")
        print(f"Repositório: {repository_data['full_name']}")
        print(f"Projeto Notion localizado: {notion_page_id}")
        print(f"Branch principal: {repository_data['default_branch']}")

        if activity:
            print(f"Última atividade: {activity['message']}")
            print(f"Branch da atividade: {activity.get('branch') or '-'}")
            references = extract_issue_references(activity["message"])
            if references:
                formatted = ", ".join(f"#{number}" for number in references)
                print(f"Referências detectadas para integração futura: {formatted}")

        return 0
    except Exception as exc:
        print(f"Erro na sincronização: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
