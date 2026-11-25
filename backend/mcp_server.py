"""Read-only stdio MCP tools for the authenticated TalentFlow API."""

import ipaddress
import os
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("TalentFlow Recruitment Platform")
_access_token: str | None = None


def _api_base_url() -> str:
    value = os.environ.get("TALENTFLOW_API_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("TALENTFLOW_API_URL must be an HTTP loopback URL.")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("TALENTFLOW_API_URL must be an HTTP origin without a path or query.")
    try:
        is_loopback = parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise ValueError("TALENTFLOW_API_URL must point to localhost or a loopback IP address.")
    return value


async def _login(client: httpx.AsyncClient, base_url: str) -> str:
    email = os.environ.get("TALENTFLOW_EMAIL", "").strip()
    password = os.environ.get("TALENTFLOW_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("Set TALENTFLOW_EMAIL and TALENTFLOW_PASSWORD in the MCP client configuration.")
    response = await client.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
    )
    if response.is_error:
        raise RuntimeError(f"TalentFlow login failed with HTTP {response.status_code}.")
    payload = response.json()
    if payload.get("role") != "admin":
        raise RuntimeError("TalentFlow MCP tools require an admin account.")
    return payload["access_token"]


async def _api_request(method: str, path: str, **kwargs: Any) -> Any:
    global _access_token
    base_url = _api_base_url()
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        if _access_token is None:
            _access_token = await _login(client, base_url)
        response = await client.request(
            method,
            f"{base_url}{path}",
            headers={"Authorization": f"Bearer {_access_token}"},
            **kwargs,
        )
        if response.status_code == 401:
            _access_token = await _login(client, base_url)
            response = await client.request(
                method,
                f"{base_url}{path}",
                headers={"Authorization": f"Bearer {_access_token}"},
                **kwargs,
            )
        if response.status_code == 403:
            raise RuntimeError("TalentFlow denied this request; an admin account is required.")
        if response.is_error:
            raise RuntimeError(f"TalentFlow API request failed with HTTP {response.status_code}.")
        return response.json()


@mcp.tool()
async def list_jobs(status: str | None = None) -> list[dict[str, Any]]:
    """List TalentFlow jobs, optionally filtered by status."""
    params = {"status": status} if status else None
    return await _api_request("GET", "/api/jobs", params=params)


@mcp.tool()
async def search_candidates(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Find candidates by semantic similarity to a natural-language query."""
    if len(query.strip()) < 2:
        raise ValueError("query must contain at least two non-whitespace characters.")
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50.")
    return await _api_request(
        "POST",
        "/api/search/candidates",
        json={"query": query.strip(), "top_k": top_k},
    )


@mcp.tool()
async def answer_candidate_question(question: str, top_k: int = 5) -> dict[str, Any]:
    """Answer an admin's question using retrieved candidate evidence and citations."""
    if len(question.strip()) < 3:
        raise ValueError("question must contain at least three non-whitespace characters.")
    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10.")
    return await _api_request(
        "POST",
        "/api/search/answer",
        json={"question": question.strip(), "top_k": top_k},
    )


@mcp.tool()
async def get_job_matches(job_id: int) -> list[dict[str, Any]]:
    """Get the stored ranked candidate matches for a job."""
    if job_id < 1:
        raise ValueError("job_id must be a positive integer.")
    return await _api_request("GET", f"/api/matching/jobs/{job_id}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
