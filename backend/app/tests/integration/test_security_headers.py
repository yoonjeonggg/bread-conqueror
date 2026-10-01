"""API 응답 보안 헤더."""

import pytest


@pytest.mark.asyncio
async def test_api_responses_carry_security_headers(client):
    r = await client.get("/api/v1/stores?lat=37.5&lng=127.0&radius_m=1000")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_error_responses_also_carry_security_headers(client):
    r = await client.get("/api/v1/stores/999999")
    assert r.status_code == 404
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_swagger_docs_are_not_blocked_by_api_csp(client):
    r = await client.get("/docs")
    assert r.status_code == 200
    assert "content-security-policy" not in r.headers
    assert r.headers["x-content-type-options"] == "nosniff"
