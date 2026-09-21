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


@patch("statscard.github_client.time.sleep")
@patch("statscard.github_client.requests.post")
def test_run_graphql_query_retries_transient_502_then_succeeds(mock_post, mock_sleep):
    mock_post.side_effect = [
        _mock_response(502, "<html>502 Bad Gateway</html>"),
        _mock_response(200, {"data": {"viewer": {"id": "abc"}}}),
    ]

    result = run_graphql_query("query { viewer { id } }", {}, "fake-token")

    assert result == {"viewer": {"id": "abc"}}
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@patch("statscard.github_client.time.sleep")
@patch("statscard.github_client.requests.post")
def test_run_graphql_query_gives_up_after_max_retries_on_persistent_502(mock_post, mock_sleep):
    mock_post.return_value = _mock_response(502, "<html>502 Bad Gateway</html>")

    with pytest.raises(GitHubAPIError):
        run_graphql_query("query {}", {}, "fake-token")

    assert mock_post.call_count == 3


@patch("statscard.github_client.time.sleep")
@patch("statscard.github_client.requests.post")
def test_run_graphql_query_does_not_retry_non_retryable_status(mock_post, mock_sleep):
    mock_post.return_value = _mock_response(401, {"message": "Bad credentials"})

    with pytest.raises(GitHubAPIError):
        run_graphql_query("query {}", {}, "bad-token")

    assert mock_post.call_count == 1
    mock_sleep.assert_not_called()
