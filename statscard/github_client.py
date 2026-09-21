from __future__ import annotations

import time

import requests

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub GraphQL API returns an HTTP error or a GraphQL error."""


def _is_retryable(status_code: int) -> bool:
    return status_code >= 500


def run_graphql_query(query: str, variables: dict, token: str) -> dict:
    """POST a GraphQL query to the GitHub API and return the `data` payload.

    Transient 5xx responses (e.g. a momentary 502 from GitHub's edge) are
    retried with linear backoff before giving up, since this runs
    unattended on a daily schedule with no human around to re-run it.
    """
    last_error: GitHubAPIError | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if response.status_code != 200:
            last_error = GitHubAPIError(f"GitHub API returned {response.status_code}: {response.text}")
            if attempt < MAX_RETRIES and _is_retryable(response.status_code):
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            raise last_error
        payload = response.json()
        if "errors" in payload:
            raise GitHubAPIError(f"GitHub GraphQL errors: {payload['errors']}")
        return payload["data"]
    raise last_error
