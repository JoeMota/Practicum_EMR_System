"""Live-path smoke: MFA challenge → token → courses → patients."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# Skip if the demo seed was never run (CI without Postgres demo data).
pytestmark = pytest.mark.asyncio


async def test_mfa_login_and_list_patients():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        if health.status_code != 200:
            pytest.skip("database not available")

        challenge = await client.post(
            "/api/v1/auth/challenge",
            json={"email": "daniel.reyes@miners.utep.edu", "password": "practicum1"},
        )
        if challenge.status_code == 401:
            pytest.skip("demo users not seeded")
        assert challenge.status_code == 200
        cid = challenge.json()["challengeId"]

        send = await client.post(
            "/api/v1/auth/send-code",
            json={"challengeId": cid, "channel": "email"},
        )
        assert send.status_code == 204

        verify = await client.post(
            "/api/v1/auth/verify-code",
            json={"challengeId": cid, "code": "123456"},
        )
        assert verify.status_code == 200
        data = verify.json()
        token = data["access_token"]
        user = data["user"]
        assert user["fullName"] == "Daniel Reyes"
        assert any(r["role"] == "student" for r in user["roles"])
        course_id = user["roles"][0]["courseIds"][0]

        headers = {"Authorization": f"Bearer {token}"}
        courses = await client.get("/api/v1/courses", headers=headers)
        assert courses.status_code == 200
        assert any(c["id"] == course_id for c in courses.json())

        patients = await client.get(
            f"/api/v1/patients?courseId={course_id}&role=student",
            headers=headers,
        )
        assert patients.status_code == 200
        rows = patients.json()
        assert len(rows) >= 1
        assert all("patient" in r for r in rows)
