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
