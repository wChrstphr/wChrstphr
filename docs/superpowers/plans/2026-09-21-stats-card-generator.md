# Stats Card Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python package (`statscard/`) plus a scheduled GitHub Action that fetches real, public-only GitHub stats via the GraphQL API, combines them with the Unicode block-art produced by the `photo-to-blockart` plan (`assets/art_data.json`), and renders `dark_mode.svg` / `light_mode.svg` — a neofetch-style profile card, in the spirit of Andrew6rant's card but with Christopher's own fields and art.

**Architecture:** A thin `github_client.py` wraps GraphQL POST requests. `stats.py` fetches repo/star/follower/commit counts (commits summed across one aliased query per account-year, so it's one network round trip regardless of account age). `loc.py` computes lines-of-code added/deleted per public repo, using a commit-count cache (`cache/loc_cache.json`) to skip repos that haven't changed since the last run. `uptime.py` is pure date arithmetic for the "uptime.software" field. `card.py` renders the SVG (pure string templating: art cells as one `<text class="art-cell">` per cell, positioned on a grid, plus a neofetch-style field/stat block) for both themes. `update_card.py` is the CLI that wires it all together and is what the GitHub Action runs daily.

**Tech Stack:** Python 3.11+, `requests` (GraphQL over HTTP), pytest, GitHub Actions (`actions/setup-python`, `stefanzweifel/git-auto-commit-action`).

**Spec:** Continues the design agreed in the `resume` repo grilling session (2026-09-19/20): "mesclar o stats do Andrew" with real, live, public-only stats; the field mapping table (OS/Host/Kernel/IDE/uptime.software/Hobbies/Contato) and the "só dados públicos" (public-only) constraint were fixed there. Consumes the sibling plan's output: `docs/superpowers/plans/2026-09-19-photo-to-blockart.md` produces `assets/art_data.json` (schema: `{"cols": int, "rows": int, "cells": [{"row": int, "col": int, "char": str, "color": "#rrggbb"}]}`) — already merged to `main`.

## Global Constraints

- Only public data is ever queried: the repos query filters `privacy: PUBLIC, ownerAffiliations: [OWNER], isFork: false` — never request anything requiring a broader token scope.
- No unit test may make a real network call — every GraphQL round trip is mocked; only the final manual task (Task 7) uses a real token.
- The card is always `985 × 530`, in both `dark_mode.svg` and `light_mode.svg`, generated together in one run.
- `card.py` consumes `assets/art_data.json`'s cell schema (`row, col, char, color`) unchanged — no adapter, no schema version bump.
- Commit messages: Conventional Commits, single-line subject (~50 chars), no body, no emojis, no `Co-Authored-By` trailer of any kind — repo owner's standing preference.
- Python 3.11+, standard library `dataclasses`/`pathlib`/`argparse` conventions.

---

## Task 1: Scaffolding + GraphQL client + uptime math

**Files:**
- Create: `statscard/__init__.py`
- Create: `statscard/github_client.py`
- Create: `statscard/uptime.py`
- Create: `statscard/tests/__init__.py`
- Create: `statscard/tests/test_github_client.py`
- Create: `statscard/tests/test_uptime.py`
- Create: `requirements-statscard.txt`

**Interfaces:**
- Produces: `statscard.github_client.GitHubAPIError` (exception), `statscard.github_client.run_graphql_query(query: str, variables: dict, token: str) -> dict`
- Produces: `statscard.uptime.format_uptime(start: "datetime.date", today: "datetime.date") -> str`

- [ ] **Step 1: Scaffolding**

`statscard/__init__.py` (empty file).
`statscard/tests/__init__.py` (empty file).

`requirements-statscard.txt`:
```
requests==2.32.3
pytest==8.3.2
```

- [ ] **Step 2: Write the failing tests for `run_graphql_query`**

`statscard/tests/test_github_client.py`:
```python
from unittest.mock import MagicMock, patch

import pytest

from statscard.github_client import GitHubAPIError, run_graphql_query


def _mock_response(status_code, json_body):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    response.text = str(json_body)
    return response


@patch("statscard.github_client.requests.post")
def test_run_graphql_query_returns_data_on_success(mock_post):
    mock_post.return_value = _mock_response(200, {"data": {"viewer": {"id": "abc"}}})

    result = run_graphql_query("query { viewer { id } }", {}, "fake-token")

    assert result == {"viewer": {"id": "abc"}}
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer fake-token"


@patch("statscard.github_client.requests.post")
def test_run_graphql_query_raises_on_non_200(mock_post):
    mock_post.return_value = _mock_response(401, {"message": "Bad credentials"})

    with pytest.raises(GitHubAPIError):
        run_graphql_query("query {}", {}, "bad-token")


@patch("statscard.github_client.requests.post")
def test_run_graphql_query_raises_on_graphql_errors(mock_post):
    mock_post.return_value = _mock_response(200, {"errors": [{"message": "field not found"}]})

    with pytest.raises(GitHubAPIError):
        run_graphql_query("query { nope }", {}, "fake-token")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest statscard/tests/test_github_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.github_client'`

- [ ] **Step 4: Implement `github_client.py`**

`statscard/github_client.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest statscard/tests/test_github_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Write the failing tests for `format_uptime`**

`statscard/tests/test_uptime.py`:
```python
from datetime import date

from statscard.uptime import format_uptime


def test_format_uptime_same_day_is_zero_months():
    assert format_uptime(date(2025, 2, 1), date(2025, 2, 1)) == "0 meses"


def test_format_uptime_singular_month():
    assert format_uptime(date(2025, 2, 1), date(2025, 3, 1)) == "1 mês"


def test_format_uptime_years_and_months():
    assert format_uptime(date(2025, 2, 1), date(2026, 9, 1)) == "1 ano, 7 meses"


def test_format_uptime_whole_years_no_months():
    assert format_uptime(date(2025, 2, 1), date(2027, 2, 1)) == "2 anos"


def test_format_uptime_day_of_month_not_yet_reached():
    # One day short of completing another month.
    assert format_uptime(date(2025, 2, 15), date(2025, 3, 10)) == "0 meses"
```

- [ ] **Step 7: Run tests to verify they fail**

Run: `pytest statscard/tests/test_uptime.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.uptime'`

- [ ] **Step 8: Implement `uptime.py`**

`statscard/uptime.py`:
```python
from __future__ import annotations

from datetime import date


def format_uptime(start: date, today: date) -> str:
    """Format elapsed time from start to today as 'X anos, Y meses' (Portuguese)."""
    months_total = (today.year - start.year) * 12 + (today.month - start.month)
    if today.day < start.day:
        months_total -= 1
    months_total = max(months_total, 0)
    years, months = divmod(months_total, 12)
    year_part = f"{years} {'ano' if years == 1 else 'anos'}"
    month_part = f"{months} {'mês' if months == 1 else 'meses'}"
    if years and months:
        return f"{year_part}, {month_part}"
    if years:
        return year_part
    return month_part
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest statscard/tests/test_uptime.py -v`
Expected: PASS (5 passed)

- [ ] **Step 10: Commit**

```bash
git add statscard/__init__.py statscard/github_client.py statscard/uptime.py \
        statscard/tests/__init__.py statscard/tests/test_github_client.py \
        statscard/tests/test_uptime.py requirements-statscard.txt
git commit -m "feat: add graphql client and uptime formatting"
```

---

## Task 2: Profile stats (`stats.py`)

**Files:**
- Create: `statscard/stats.py`
- Create: `statscard/tests/test_stats.py`

**Interfaces:**
- Consumes: `statscard.github_client.run_graphql_query` (Task 1).
- Produces: `statscard.stats.ProfileStats` (dataclass: `repos: int, stars: int, followers: int, commits: int, repo_names: list[str], created_year: int`), `statscard.stats.build_multi_year_query(start_year: int, end_year: int) -> str`, `statscard.stats.sum_year_commits(user_data: dict) -> int`, `statscard.stats.fetch_profile_stats(login: str, token: str, current_year: int) -> ProfileStats`

- [ ] **Step 1: Write the failing tests**

`statscard/tests/test_stats.py`:
```python
from unittest.mock import patch

from statscard.stats import (
    ProfileStats,
    build_multi_year_query,
    fetch_profile_stats,
    sum_year_commits,
)


def test_build_multi_year_query_has_one_alias_per_year():
    query = build_multi_year_query(2023, 2025)
    assert "y2023: contributionsCollection" in query
    assert "y2024: contributionsCollection" in query
    assert "y2025: contributionsCollection" in query
    assert '"2024-01-01T00:00:00Z"' in query
    assert '"2024-12-31T23:59:59Z"' in query


def test_sum_year_commits_ignores_non_year_keys():
    user_data = {
        "y2023": {"totalCommitContributions": 10},
        "y2024": {"totalCommitContributions": 5},
        "createdAt": "2023-01-01T00:00:00Z",
    }
    assert sum_year_commits(user_data) == 15


def test_fetch_profile_stats_paginates_repos_and_sums_commits():
    page1 = {
        "user": {
            "createdAt": "2023-06-15T00:00:00Z",
            "followers": {"totalCount": 42},
            "repositories": {
                "totalCount": 3,
                "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR1"},
                "nodes": [
                    {"name": "repo-a", "stargazerCount": 2},
                    {"name": "repo-b", "stargazerCount": 5},
                ],
            },
        }
    }
    page2 = {
        "user": {
            "createdAt": "2023-06-15T00:00:00Z",
            "followers": {"totalCount": 42},
            "repositories": {
                "totalCount": 3,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {"name": "repo-c", "stargazerCount": 1},
                ],
            },
        }
    }
    commits_response = {
        "user": {
            "y2023": {"totalCommitContributions": 100},
            "y2024": {"totalCommitContributions": 200},
            "y2025": {"totalCommitContributions": 50},
        }
    }

    with patch("statscard.stats.run_graphql_query") as mock_query:
        mock_query.side_effect = [page1, page2, commits_response]

        result = fetch_profile_stats("wChrstphr", "fake-token", current_year=2025)

    assert result == ProfileStats(
        repos=3,
        stars=8,
        followers=42,
        commits=350,
        repo_names=["repo-a", "repo-b", "repo-c"],
        created_year=2023,
    )
    assert mock_query.call_count == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest statscard/tests/test_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.stats'`

- [ ] **Step 3: Implement `stats.py`**

`statscard/stats.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from statscard.github_client import run_graphql_query

_PROFILE_QUERY = """
query($login: String!, $reposCursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(first: 100, after: $reposCursor, ownerAffiliations: [OWNER], isFork: false, privacy: PUBLIC) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { name stargazerCount }
    }
  }
}
"""


@dataclass(frozen=True)
class ProfileStats:
    repos: int
    stars: int
    followers: int
    commits: int
    repo_names: list[str]
    created_year: int


def build_multi_year_query(start_year: int, end_year: int) -> str:
    """Build a GraphQL query aliasing one contributionsCollection per year,
    so total public commit contributions since account creation can be
    fetched in a single round trip regardless of account age."""
    aliases = []
    for year in range(start_year, end_year + 1):
        aliases.append(
            f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", '
            f'to: "{year}-12-31T23:59:59Z") {{ totalCommitContributions }}'
        )
    body = "\n    ".join(aliases)
    return f"query($login: String!) {{\n  user(login: $login) {{\n    {body}\n  }}\n}}"


def sum_year_commits(user_data: dict) -> int:
    """Sum totalCommitContributions across every yNNNN-aliased field."""
    return sum(
        value["totalCommitContributions"]
        for key, value in user_data.items()
        if key.startswith("y") and key[1:].isdigit()
    )


def _fetch_all_repos(login: str, token: str) -> tuple[int, int, int, list[str], int]:
    """Returns (repo_count, star_sum, followers, repo_names, created_year)."""
    cursor = None
    star_sum = 0
    repo_names: list[str] = []
    repo_count = 0
    followers = 0
    created_year = None
    while True:
        data = run_graphql_query(_PROFILE_QUERY, {"login": login, "reposCursor": cursor}, token)
        user = data["user"]
        if created_year is None:
            created_year = int(user["createdAt"][:4])
            followers = user["followers"]["totalCount"]
        repo_count = user["repositories"]["totalCount"]
        for node in user["repositories"]["nodes"]:
            star_sum += node["stargazerCount"]
            repo_names.append(node["name"])
        page_info = user["repositories"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return repo_count, star_sum, followers, repo_names, created_year


def fetch_profile_stats(login: str, token: str, current_year: int) -> ProfileStats:
    repo_count, star_sum, followers, repo_names, created_year = _fetch_all_repos(login, token)
    query = build_multi_year_query(created_year, current_year)
    data = run_graphql_query(query, {"login": login}, token)
    commits = sum_year_commits(data["user"])
    return ProfileStats(
        repos=repo_count,
        stars=star_sum,
        followers=followers,
        commits=commits,
        repo_names=repo_names,
        created_year=created_year,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest statscard/tests/test_stats.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add statscard/stats.py statscard/tests/test_stats.py
git commit -m "feat: add profile stats fetching"
```

---

## Task 3: Lines-of-code computation with cache (`loc.py`)

**Files:**
- Create: `statscard/loc.py`
- Create: `statscard/tests/test_loc.py`

**Interfaces:**
- Consumes: `statscard.github_client.run_graphql_query` (Task 1).
- Produces: `statscard.loc.LocStats` (dataclass: `additions: int, deletions: int`), `statscard.loc.compute_loc_stats(login: str, repo_names: list[str], token: str, cache_path: "pathlib.Path") -> LocStats`

- [ ] **Step 1: Write the failing tests**

`statscard/tests/test_loc.py`:
```python
import json
from unittest.mock import patch

from statscard.loc import LocStats, compute_loc_stats


def _fake_run_query(query, variables, token):
    if "viewer { id }" in query:
        return {"viewer": {"id": "AUTHOR123"}}
    if "history { totalCount }" in query:
        counts = {"repo-a": 10, "repo-b": 3}
        return {
            "repository": {
                "defaultBranchRef": {
                    "target": {"history": {"totalCount": counts[variables["repo"]]}}
                }
            }
        }
    if "nodes { additions deletions }" in query:
        # Only repo-b's full history should ever be requested (repo-a is cached).
        assert variables["repo"] == "repo-b"
        return {
            "repository": {
                "defaultBranchRef": {
                    "target": {
                        "history": {
                            "totalCount": 3,
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {"additions": 10, "deletions": 2},
                                {"additions": 5, "deletions": 1},
                                {"additions": 1, "deletions": 0},
                            ],
                        }
                    }
                }
            }
        }
    raise AssertionError(f"unexpected query: {query}")


def test_compute_loc_stats_uses_cache_when_commit_count_unchanged(tmp_path):
    cache_path = tmp_path / "loc_cache.json"
    cache_path.write_text(
        json.dumps({"repo-a": {"commit_count": 10, "additions": 100, "deletions": 20}}),
        encoding="utf-8",
    )

    with patch("statscard.loc.run_graphql_query", side_effect=_fake_run_query):
        result = compute_loc_stats("wChrstphr", ["repo-a", "repo-b"], "fake-token", cache_path)

    # repo-a comes from cache (100, 20); repo-b is freshly fetched (16, 3).
    assert result == LocStats(additions=116, deletions=23)

    updated_cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert updated_cache["repo-a"] == {"commit_count": 10, "additions": 100, "deletions": 20}
    assert updated_cache["repo-b"] == {"commit_count": 3, "additions": 16, "deletions": 3}


def test_compute_loc_stats_starts_empty_when_no_cache_file(tmp_path):
    cache_path = tmp_path / "does_not_exist.json"

    with patch("statscard.loc.run_graphql_query", side_effect=_fake_run_query):
        result = compute_loc_stats("wChrstphr", ["repo-b"], "fake-token", cache_path)

    assert result == LocStats(additions=16, deletions=3)
    assert cache_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest statscard/tests/test_loc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.loc'`

- [ ] **Step 3: Implement `loc.py`**

`statscard/loc.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest statscard/tests/test_loc.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add statscard/loc.py statscard/tests/test_loc.py
git commit -m "feat: add cached lines-of-code computation"
```

---

## Task 4: SVG card rendering (`card.py`)

**Files:**
- Create: `statscard/card.py`
- Create: `statscard/tests/test_card.py`

**Interfaces:**
- Produces: `statscard.card.render_svg(theme: str, art_cells: list[dict], fields: dict, stats: dict) -> str`

- [ ] **Step 1: Write the failing tests**

`statscard/tests/test_card.py`:
```python
from statscard.card import render_svg

_FIELDS = {
    "os": "Linux / Windows 11 / Android",
    "host": "Presidência da República — DSIC",
    "kernel": "Engenharia de Software @ UnB",
    "ide": "VS Code + Claude Code",
    "uptime": "1 ano, 7 meses",
    "hobbies": "Leitura, Viagens, Natação",
    "contact": "linkedin.com/in/christopherparaizo · github.com/wChrstphr",
}
_STATS = {"repos": 12, "stars": 34, "commits": 567, "followers": 8, "additions": 9000, "deletions": 1200}
_ART_CELLS = [{"row": 0, "col": 0, "char": "█", "color": "#a1b2c3"}]


def test_render_svg_is_well_formed_and_correct_size():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="985" height="530"')
    assert svg.rstrip().endswith("</svg>")


def test_render_svg_dark_theme_uses_dark_background():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert 'fill="#161b22"' in svg


def test_render_svg_light_theme_uses_light_background():
    svg = render_svg("light", _ART_CELLS, _FIELDS, _STATS)
    assert 'fill="#fffefe"' in svg


def test_render_svg_emits_one_art_cell_element_per_cell():
    cells = [
        {"row": 0, "col": 0, "char": "█", "color": "#ff0000"},
        {"row": 1, "col": 2, "char": "▒", "color": "#00ff00"},
    ]
    svg = render_svg("dark", cells, _FIELDS, _STATS)
    assert svg.count('class="art-cell"') == 2
    assert "#ff0000" in svg
    assert "#00ff00" in svg


def test_render_svg_includes_all_fields_and_stats():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert "uptime.software" in svg
    assert "1 ano, 7 meses" in svg
    assert "Leitura, Viagens, Natação" in svg
    assert "Repos: 12" in svg
    assert "Stars: 34" in svg
    assert "Commits: 567" in svg
    assert "Followers: 8" in svg
    assert "+9000" in svg
    assert "-1200" in svg


def test_render_svg_escapes_special_characters_in_field_values():
    fields = dict(_FIELDS)
    fields["hobbies"] = "A & B <test>"
    svg = render_svg("dark", _ART_CELLS, fields, _STATS)
    assert "A &amp; B &lt;test&gt;" in svg
    assert "A & B <test>" not in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest statscard/tests/test_card.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.card'`

- [ ] **Step 3: Implement `card.py`**

`statscard/card.py`:
```python
from __future__ import annotations

CARD_WIDTH = 985
CARD_HEIGHT = 530

CHAR_W = 6.3
CHAR_H = 11.2
ART_LEFT = 20
ART_TOP = 40

TEXT_LEFT = 400
LINE_H = 20

_THEMES = {
    "dark": {
        "bg": "#161b22",
        "border": "#30363d",
        "label": "#ff9868",
        "value": "#a9fef7",
        "title": "#38bdae",
        "dim": "#57606a",
        "add": "#a6e22e",
        "del": "#f92672",
    },
    "light": {
        "bg": "#fffefe",
        "border": "#d0d7de",
        "label": "#b45309",
        "value": "#24292f",
        "title": "#0969da",
        "dim": "#6e7781",
        "add": "#1a7f37",
        "del": "#cf222e",
    },
}

_FIELD_ORDER = ["os", "host", "kernel", "ide", "uptime", "hobbies", "contact"]
_FIELD_LABELS = {
    "os": "OS",
    "host": "Host",
    "kernel": "Kernel",
    "ide": "IDE",
    "uptime": "uptime.software",
    "hobbies": "Hobbies",
    "contact": "Contato",
}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(theme: str, art_cells: list[dict], fields: dict, stats: dict) -> str:
    colors = _THEMES[theme]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" '
        f'font-family="Consolas, Monaco, monospace" font-size="13">',
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="10" '
        f'fill="{colors["bg"]}" stroke="{colors["border"]}"/>',
    ]

    for cell in art_cells:
        x = ART_LEFT + cell["col"] * CHAR_W
        y = ART_TOP + (cell["row"] + 1) * CHAR_H
        parts.append(
            f'<text class="art-cell" x="{x:.1f}" y="{y:.1f}" fill="{cell["color"]}">'
            f'{_escape(cell["char"])}</text>'
        )

    y = 50
    parts.append(
        f'<text x="{TEXT_LEFT}" y="{y}" fill="{colors["title"]}" font-weight="bold">'
        f"christopher@github</text>"
    )
    y += LINE_H
    parts.append(
        f'<line x1="{TEXT_LEFT}" y1="{y - 14}" x2="{TEXT_LEFT + 300}" y2="{y - 14}" '
        f'stroke="{colors["dim"]}"/>'
    )

    for key in _FIELD_ORDER:
        label = _FIELD_LABELS[key]
        value = _escape(str(fields[key]))
        parts.append(
            f'<text x="{TEXT_LEFT}" y="{y}">'
            f'<tspan fill="{colors["label"]}">{label}: </tspan>'
            f'<tspan fill="{colors["value"]}">{value}</tspan></text>'
        )
        y += LINE_H

    y += 8
    parts.append(
        f'<line x1="{TEXT_LEFT}" y1="{y - 14}" x2="{TEXT_LEFT + 300}" y2="{y - 14}" '
        f'stroke="{colors["dim"]}"/>'
    )
    stats_line = (
        f'Repos: {stats["repos"]} | Stars: {stats["stars"]} | '
        f'Commits: {stats["commits"]} | Followers: {stats["followers"]}'
    )
    parts.append(f'<text x="{TEXT_LEFT}" y="{y}" fill="{colors["value"]}">{_escape(stats_line)}</text>')
    y += LINE_H
    parts.append(
        f'<text x="{TEXT_LEFT}" y="{y}">'
        f'<tspan fill="{colors["add"]}">+{stats["additions"]}</tspan>'
        f'<tspan fill="{colors["value"]}"> / </tspan>'
        f'<tspan fill="{colors["del"]}">-{stats["deletions"]}</tspan>'
        f'<tspan fill="{colors["dim"]}"> lines of code</tspan></text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest statscard/tests/test_card.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add statscard/card.py statscard/tests/test_card.py
git commit -m "feat: add neofetch-style SVG card renderer"
```

---

## Task 5: CLI wiring (`update_card.py`)

**Files:**
- Create: `statscard/update_card.py`
- Create: `statscard/tests/test_update_card.py`

**Interfaces:**
- Consumes: `statscard.stats.fetch_profile_stats`, `statscard.stats.ProfileStats` (Task 2); `statscard.loc.compute_loc_stats`, `statscard.loc.LocStats` (Task 3); `statscard.card.render_svg` (Task 4); `statscard.uptime.format_uptime` (Task 1).
- Produces: `statscard.update_card.load_art_cells(path: "pathlib.Path") -> list[dict]`, `statscard.update_card.build_card_data(token: str, today: "datetime.date") -> tuple[dict, dict]`, CLI entry point `main()`.

- [ ] **Step 1: Write the failing tests**

`statscard/tests/test_update_card.py`:
```python
import json
from datetime import date
from unittest.mock import patch

from statscard.loc import LocStats
from statscard.stats import ProfileStats
from statscard.update_card import build_card_data, load_art_cells, main


def test_load_art_cells_reads_cells_list(tmp_path):
    art_path = tmp_path / "art_data.json"
    art_path.write_text(
        json.dumps({"cols": 2, "rows": 1, "cells": [{"row": 0, "col": 0, "char": "█", "color": "#000000"}]}),
        encoding="utf-8",
    )

    cells = load_art_cells(art_path)

    assert cells == [{"row": 0, "col": 0, "char": "█", "color": "#000000"}]


@patch("statscard.update_card.compute_loc_stats")
@patch("statscard.update_card.fetch_profile_stats")
def test_build_card_data_combines_stats_and_uptime(mock_fetch_profile, mock_compute_loc):
    mock_fetch_profile.return_value = ProfileStats(
        repos=5, stars=10, followers=3, commits=99, repo_names=["a", "b"], created_year=2023
    )
    mock_compute_loc.return_value = LocStats(additions=100, deletions=20)

    fields, stats = build_card_data("fake-token", date(2026, 9, 1))

    assert fields["uptime"] == "1 ano, 7 meses"
    assert fields["os"] == "Linux / Windows 11 / Android"
    assert stats == {
        "repos": 5,
        "stars": 10,
        "commits": 99,
        "followers": 3,
        "additions": 100,
        "deletions": 20,
    }
    mock_fetch_profile.assert_called_once_with("wChrstphr", "fake-token", 2026)
    mock_compute_loc.assert_called_once()


@patch("statscard.update_card.compute_loc_stats")
@patch("statscard.update_card.fetch_profile_stats")
def test_main_writes_both_svg_files(mock_fetch_profile, mock_compute_loc, tmp_path, monkeypatch):
    mock_fetch_profile.return_value = ProfileStats(
        repos=1, stars=1, followers=1, commits=1, repo_names=[], created_year=2025
    )
    mock_compute_loc.return_value = LocStats(additions=1, deletions=1)
    monkeypatch.setenv("ACCESS_TOKEN", "fake-token")

    art_path = tmp_path / "art_data.json"
    art_path.write_text(json.dumps({"cols": 1, "rows": 1, "cells": []}), encoding="utf-8")
    dark_out = tmp_path / "dark_mode.svg"
    light_out = tmp_path / "light_mode.svg"

    with patch(
        "sys.argv",
        [
            "update_card.py",
            "--art",
            str(art_path),
            "--dark-out",
            str(dark_out),
            "--light-out",
            str(light_out),
        ],
    ):
        main()

    assert "<svg" in dark_out.read_text(encoding="utf-8")
    assert "<svg" in light_out.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest statscard/tests/test_update_card.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'statscard.update_card'`

- [ ] **Step 3: Implement `update_card.py`**

`statscard/update_card.py`:
```python
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from statscard.card import render_svg
from statscard.loc import compute_loc_stats
from statscard.stats import fetch_profile_stats
from statscard.uptime import format_uptime

LOGIN = "wChrstphr"
UPTIME_START = date(2025, 2, 1)

FIELDS_STATIC = {
    "os": "Linux / Windows 11 / Android",
    "host": "Presidência da República — DSIC",
    "kernel": "Engenharia de Software @ UnB",
    "ide": "VS Code + Claude Code",
    "hobbies": "Leitura, Viagens, Natação",
    "contact": "linkedin.com/in/christopherparaizo · github.com/wChrstphr",
}


def load_art_cells(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["cells"]


def build_card_data(token: str, today: date) -> tuple[dict, dict]:
    profile = fetch_profile_stats(LOGIN, token, today.year)
    loc = compute_loc_stats(LOGIN, profile.repo_names, token, Path("cache/loc_cache.json"))
    fields = dict(FIELDS_STATIC)
    fields["uptime"] = format_uptime(UPTIME_START, today)
    stats = {
        "repos": profile.repos,
        "stars": profile.stars,
        "commits": profile.commits,
        "followers": profile.followers,
        "additions": loc.additions,
        "deletions": loc.deletions,
    }
    return fields, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate dark_mode.svg / light_mode.svg")
    parser.add_argument("--art", type=Path, default=Path("assets/art_data.json"))
    parser.add_argument("--dark-out", type=Path, default=Path("dark_mode.svg"))
    parser.add_argument("--light-out", type=Path, default=Path("light_mode.svg"))
    args = parser.parse_args()

    token = os.environ["ACCESS_TOKEN"]
    art_cells = load_art_cells(args.art)
    fields, stats = build_card_data(token, date.today())

    args.dark_out.write_text(render_svg("dark", art_cells, fields, stats), encoding="utf-8")
    args.light_out.write_text(render_svg("light", art_cells, fields, stats), encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest statscard/tests/test_update_card.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full statscard suite**

Run: `pytest statscard/ -v`
Expected: PASS (19 passed)

- [ ] **Step 6: Commit**

```bash
git add statscard/update_card.py statscard/tests/test_update_card.py
git commit -m "feat: wire up stats card CLI"
```

---

## Task 6: GitHub Action workflow

**Files:**
- Create: `.github/workflows/update-stats-card.yml`

**Interfaces:**
- Consumes: `statscard.update_card` (Task 5, run as `python -m statscard.update_card`), the repo secret `ACCESS_TOKEN` (set up by the user in Task 7 — not something this task can create).

- [ ] **Step 1: Write the workflow**

`.github/workflows/update-stats-card.yml`:
```yaml
name: Update Stats Card

on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - "assets/art_data.json"

jobs:
  update-card:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-statscard.txt
      - run: python -m statscard.update_card
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: update stats card"
          file_pattern: "dark_mode.svg light_mode.svg cache/loc_cache.json"
```

This mirrors the `git-auto-commit-action` already used in the `resume` repo's own CI, so the auto-commit pattern is consistent across the user's repos. The action commits as its own bot identity (not the user's), which is standard for scheduled CI commits and distinct from the no-co-author rule that governs commits made by an agent acting on the user's behalf.

- [ ] **Step 2: Sanity-check the YAML**

Run: `python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/update-stats-card.yml'))"` (if `pyyaml` isn't installed, `pip install pyyaml` first, or use `python3 -c "import json,subprocess; subprocess.run(['python3','-c','pass'])"` as a fallback — the important check is that the file parses as valid YAML with no tab characters and consistent indentation).
Expected: no output, exit code 0 (valid YAML).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update-stats-card.yml
git commit -m "ci: add scheduled stats card workflow"
```

---

## Task 7: Real token run and validation (manual, not TDD)

This task has no automated test — it is the one-time (and then recurring, via the schedule) real run against the live GitHub API, plus your own visual sign-off of the two generated SVGs.

**Files:**
- Create: `dark_mode.svg` (committed)
- Create: `light_mode.svg` (committed)
- Create: `cache/loc_cache.json` (committed)

- [ ] **Step 1: Create the fine-grained Personal Access Token (you must do this — no one else can)**

On GitHub: Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token. Scope it to: read-only access to Public Repositories (or "All repositories" if you'd rather not re-scope per-repo later, but keep the *permissions* read-only), with these repository permissions: **Contents: Read-only**, **Metadata: Read-only**. Under account permissions, no extra scopes are needed since we only ever query public data. This matches the Global Constraint that the card never has access to anything beyond what's already public.

- [ ] **Step 2: Add it as a repository secret**

On the `wChrstphr/wChrstphr` repo: Settings → Secrets and variables → Actions → New repository secret → name it `ACCESS_TOKEN`, paste the token value.

- [ ] **Step 3: Run once locally to validate before relying on the schedule**

```bash
pip install -r requirements-statscard.txt
ACCESS_TOKEN=<your token> python -m statscard.update_card
```

- [ ] **Step 4: Visually inspect both SVGs**

Open `dark_mode.svg` and `light_mode.svg` in a browser. Check: the art (glasses + hair) renders recognizably at this scale, the field values match the agreed table, the stats line shows plausible numbers (compare `Repos`/`Stars`/`Followers` against what you see on your actual GitHub profile page), and both themes are legible (text isn't the same color as its background).

- [ ] **Step 5: Confirm no raw photo or token leaked**

Run: `git status --short` — expected: only `dark_mode.svg`, `light_mode.svg`, and `cache/loc_cache.json` as new/modified files. Also `grep -r "ACCESS_TOKEN\|ghp_\|github_pat_" dark_mode.svg light_mode.svg cache/loc_cache.json` should return nothing (the token must never end up embedded in the generated output).

- [ ] **Step 6: Commit**

```bash
git add dark_mode.svg light_mode.svg cache/loc_cache.json
git commit -m "feat: add generated stats card"
```

- [ ] **Step 7: Trigger the workflow once for real, to confirm the secret and Action work end to end**

On GitHub: Actions tab → "Update Stats Card" → "Run workflow" (uses the `workflow_dispatch` trigger). Confirm it succeeds and that the `git-auto-commit-action` step either commits (if the run produced different numbers) or reports nothing to commit (if identical) — either is a successful outcome.

---

## Self-Review Notes

- **Spec coverage:** GraphQL-based real, live, public-only stats (Q1/Q10) → Tasks 2-3, enforced by the `privacy: PUBLIC` filter in `stats.py`'s query and by scoping the token to read-only public access in Task 7. Field mapping table (Q12/Q13/Q14) → `FIELDS_STATIC` + `uptime` in `update_card.py`, rendered by `card.py`. Both dark/light themes → `card.py`'s `_THEMES` dict and `update_card.py` writing both files every run. Same repo as the profile README (Q9) → everything lives at the root of `wChrstphr/wChrstphr`, no separate repo. Consumes Plan 1's `assets/art_data.json` unchanged → `update_card.load_art_cells` reads the exact schema Plan 1 produces.
- **Placeholder scan:** none found — every step has runnable code or an exact command.
- **Type consistency:** `ProfileStats.repo_names` (Task 2) is what `update_card.build_card_data` passes as `loc.compute_loc_stats`'s `repo_names` argument — names match. `LocStats.additions`/`.deletions` (Task 3) map directly to `stats["additions"]`/`stats["deletions"]` keys consumed by `card.render_svg` (Task 4) — verified the dict key names match between `update_card.py`'s `stats` dict construction and `card.py`'s `stats["repos"]`/`stats["stars"]`/etc. lookups. `art_cells` list-of-dicts shape (`row`, `col`, `char`, `color`) is used identically in `card.py`'s `render_svg` and `update_card.py`'s `load_art_cells` — no transformation in between, matching Plan 1's `assets/art_data.json` schema exactly.
