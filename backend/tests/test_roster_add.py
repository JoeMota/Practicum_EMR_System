"""Roster: single-member add + list for instructors."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

GERARDO = "gerardo.sillas@utep.edu"
MFA = "123456"


async def _login(client: AsyncClient, email: str) -> str:
    challenge = await client.post("/api/v1/auth/challenge", json={"email": email, "password": "practicum1"})
    if challenge.status_code == 401:
        pytest.skip("Demo users not seeded")
    assert challenge.status_code == 200
    cid = challenge.json()["challengeId"]
    await client.post("/api/v1/auth/send-code", json={"challengeId": cid, "channel": "email"})
    verified = await client.post("/api/v1/auth/verify-code", json={"challengeId": cid, "code": MFA})
    assert verified.status_code == 200
    return verified.json()["access_token"]


@pytest.mark.asyncio
async def test_add_roster_member_one_by_one():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, GERARDO)
        headers = {"Authorization": f"Bearer {token}"}

        courses = await client.get("/api/v1/courses", headers=headers)
        assert courses.status_code == 200
        course_id = courses.json()[0]["id"]

        email = f"new.student.{uuid.uuid4().hex[:8]}@miners.utep.edu"
        res = await client.post(
            f"/api/v1/courses/{course_id}/roster/members",
            headers=headers,
            json={
                "fullName": "New Student",
                "email": email,
                "universityId": "800111222",
                "discipline": "pharmacy",
                "appRole": "student",
            },
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["created"] is True
        assert body["alreadyEnrolled"] is False
        assert body["user"]["email"] == email

        again = await client.post(
            f"/api/v1/courses/{course_id}/roster/members",
            headers=headers,
            json={
                "fullName": "New Student",
                "email": email,
                "universityId": "800111222",
                "discipline": "pharmacy",
                "appRole": "student",
            },
        )
        assert again.status_code == 201
        assert again.json()["created"] is False
        assert again.json()["alreadyEnrolled"] is True

        roster = await client.get(f"/api/v1/courses/{course_id}/roster", headers=headers)
        assert roster.status_code == 200
        emails = {u["email"] for u in roster.json()}
        assert email in emails
