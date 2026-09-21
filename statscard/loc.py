from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from statscard.github_client import run_graphql_query

_VIEWER_ID_QUERY = "query { viewer { id } }"

_COUNT_QUERY = """
query($login: String!, $repo: String!) {
  repository(owner: $login, name: $repo) {
    defaultBranchRef {
      target {
        ... on Commit {
          history { totalCount }
        }
      }
    }
  }
}
"""

_HISTORY_QUERY = """
query($login: String!, $repo: String!, $authorId: ID!, $cursor: String) {
  repository(owner: $login, name: $repo) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, after: $cursor, author: { id: $authorId }) {
            totalCount
            pageInfo { hasNextPage endCursor }
            nodes { additions deletions }
          }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class LocStats:
    additions: int
    deletions: int


def _fetch_viewer_id(token: str) -> str:
    data = run_graphql_query(_VIEWER_ID_QUERY, {}, token)
    return data["viewer"]["id"]


def _fetch_commit_count(login: str, repo: str, token: str) -> int:
    data = run_graphql_query(_COUNT_QUERY, {"login": login, "repo": repo}, token)
    ref = data["repository"]["defaultBranchRef"]
    if ref is None:
        return 0
    return ref["target"]["history"]["totalCount"]


def _fetch_repo_loc(login: str, repo: str, author_id: str, token: str) -> tuple[int, int, int]:
    """Returns (total_commits, additions, deletions) for one repo, fully paginated."""
    cursor = None
    additions = 0
    deletions = 0
    total_commits = 0
    while True:
        data = run_graphql_query(
            _HISTORY_QUERY,
            {"login": login, "repo": repo, "authorId": author_id, "cursor": cursor},
            token,
        )
        ref = data["repository"]["defaultBranchRef"]
        if ref is None:
            return 0, 0, 0
        history = ref["target"]["history"]
        total_commits = history["totalCount"]
        for node in history["nodes"]:
            additions += node["additions"]
            deletions += node["deletions"]
        page_info = history["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return total_commits, additions, deletions


def _load_cache(cache_path: Path) -> dict:
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text(encoding="utf-8"))


def _save_cache(cache_path: Path, cache: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def compute_loc_stats(login: str, repo_names: list[str], token: str, cache_path: Path) -> LocStats:
    """Sum additions/deletions across repo_names, skipping the expensive
    per-commit history fetch for any repo whose commit count matches cache.
    """
    cache = _load_cache(cache_path)
    total_additions = 0
    total_deletions = 0
    author_id = None
    for repo in repo_names:
        commit_count = _fetch_commit_count(login, repo, token)
        cached = cache.get(repo)
        if cached and cached.get("commit_count") == commit_count:
            additions, deletions = cached["additions"], cached["deletions"]
        else:
            if author_id is None:
                author_id = _fetch_viewer_id(token)
            _, additions, deletions = _fetch_repo_loc(login, repo, author_id, token)
            cache[repo] = {"commit_count": commit_count, "additions": additions, "deletions": deletions}
        total_additions += additions
        total_deletions += deletions
    _save_cache(cache_path, cache)
    return LocStats(additions=total_additions, deletions=total_deletions)
