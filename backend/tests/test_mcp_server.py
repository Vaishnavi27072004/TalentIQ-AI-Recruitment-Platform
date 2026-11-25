import pytest

from mcp_server import _api_base_url


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://example.com",
        "http://127.0.0.1:8000/api",
        "http://user:password@127.0.0.1:8000",
    ],
)
def test_mcp_api_url_rejects_non_local_or_non_origin_urls(monkeypatch, url):
    monkeypatch.setenv("TALENTFLOW_API_URL", url)

    with pytest.raises(ValueError):
        _api_base_url()


def test_mcp_api_url_accepts_loopback_origin(monkeypatch):
    monkeypatch.setenv("TALENTFLOW_API_URL", "http://127.0.0.1:8002/")

    assert _api_base_url() == "http://127.0.0.1:8002"
