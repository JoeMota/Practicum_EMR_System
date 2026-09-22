from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "docs" in body
