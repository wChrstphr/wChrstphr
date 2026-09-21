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
