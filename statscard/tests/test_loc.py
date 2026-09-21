import json
from unittest.mock import patch

from statscard.github_client import GitHubAPIError
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


def _fake_run_query_failing_history(query, variables, token):
    if "viewer { id }" in query:
        return {"viewer": {"id": "AUTHOR123"}}
    if "history { totalCount }" in query:
        return {
            "repository": {
                "defaultBranchRef": {"target": {"history": {"totalCount": 19}}}
            }
        }
    if "nodes { additions deletions }" in query:
        raise GitHubAPIError("GitHub API returned 502: <html>502 Bad Gateway</html>")
    raise AssertionError(f"unexpected query: {query}")


def test_compute_loc_stats_falls_back_to_cache_when_fetch_fails(tmp_path):
    cache_path = tmp_path / "loc_cache.json"
    cache_path.write_text(
        json.dumps({"Mestrado": {"commit_count": 5, "additions": 50, "deletions": 10}}),
        encoding="utf-8",
    )

    with patch("statscard.loc.run_graphql_query", side_effect=_fake_run_query_failing_history):
        result = compute_loc_stats("wChrstphr", ["Mestrado"], "fake-token", cache_path)

    # commit_count changed (5 -> 19) so a fresh fetch is attempted, fails, and
    # falls back to the stale cached values rather than crashing.
    assert result == LocStats(additions=50, deletions=10)


def test_compute_loc_stats_falls_back_to_zero_when_fetch_fails_and_no_cache(tmp_path):
    cache_path = tmp_path / "does_not_exist.json"

    with patch("statscard.loc.run_graphql_query", side_effect=_fake_run_query_failing_history):
        result = compute_loc_stats("wChrstphr", ["Mestrado"], "fake-token", cache_path)

    assert result == LocStats(additions=0, deletions=0)
