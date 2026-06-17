from unittest.mock import patch, MagicMock
from core.services import github_connector as gc


def test_create_pr_posts_and_returns_url():
    token = {"access_token": "t"}
    resp = MagicMock()
    resp.status_code = 201
    resp.json = lambda: {"html_url": "https://github.com/o/r/pull/5", "number": 5}
    with patch.object(gc, "get_fresh_token", return_value=token), \
         patch("httpx.post", return_value=resp) as post:
        res = gc.create_pr("u", "o/r", head="feat/x", base="main", title="T", body="B")
    assert res["status"] == "ok"
    assert res["url"] == "https://github.com/o/r/pull/5"
    assert post.call_args.kwargs["json"]["head"] == "feat/x"


def test_create_pr_no_token():
    with patch.object(gc, "get_fresh_token", return_value=None):
        res = gc.create_pr("u", "o/r", head="h", base="main", title="T", body="")
    assert res["status"] == "error"
    assert res["error"] == "github_not_connected"
