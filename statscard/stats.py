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
