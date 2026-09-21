from __future__ import annotations

import requests

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub GraphQL API returns an HTTP error or a GraphQL error."""


def run_graphql_query(query: str, variables: dict, token: str) -> dict:
    """POST a GraphQL query to the GitHub API and return the `data` payload."""
    response = requests.post(
        GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise GitHubAPIError(f"GitHub API returned {response.status_code}: {response.text}")
    payload = response.json()
    if "errors" in payload:
        raise GitHubAPIError(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]
