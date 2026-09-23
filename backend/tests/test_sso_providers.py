"""Auth provider discovery + UTEP email gate for SSO-shaped responses."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_auth_providers_default_local():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/providers")
        assert res.status_code == 200
        body = res.json()
        assert body["localMfa"] is True
        assert body["utepSso"] is False
        assert body["duo"] is False
        assert body["requireUtepSso"] is False


@pytest.mark.asyncio
async def test_sso_login_without_entra_is_unavailable():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/sso/login", follow_redirects=False)
        assert res.status_code == 503
