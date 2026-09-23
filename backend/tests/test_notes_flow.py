"""Live-path: student draft → sign → instructor cosign / return."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

DANIEL = "daniel.reyes@miners.utep.edu"
GERARDO = "gerardo.sillas@utep.edu"
PASSWORD = "practicum1"
MFA = "123456"
AE_DANIEL = "33333333-3333-3333-3333-333333333303"
GERARDO_ID = "11111111-1111-1111-1111-111111111103"


async def _mfa_login(client: AsyncClient, email: str) -> dict:
    challenge = await client.post(
        "/api/v1/auth/challenge",
        json={"email": email, "password": PASSWORD},
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
        json={"challengeId": cid, "code": MFA},
    )
    assert verify.status_code == 200
    return verify.json()


async def test_create_draft_sign_cosign_and_return():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        if health.status_code != 200:
            pytest.skip("database not available")

        # --- Student: create draft on assessment patient ---
        student = await _mfa_login(client, DANIEL)
        s_headers = {"Authorization": f"Bearer {student['access_token']}"}

        # Spoofing instructor role must fail (enrollment-backed ?role=)
        spoof = await client.get(
            f"/api/v1/patients/{AE_DANIEL}?role=instructor",
            headers=s_headers,
        )
        assert spoof.status_code == 403

        create = await client.post(
            "/api/v1/notes",
            headers=s_headers,
            json={
                "patientId": AE_DANIEL,
                "templateId": "pharmacy_mtm",
                "discipline": "pharmacy",
            },
        )
        assert create.status_code == 201, create.text
        note = create.json()
        assert note["status"] == "draft"
        note_id = note["id"]
        version = note["version"]

        patch = await client.patch(
            f"/api/v1/notes/{note_id}",
            headers=s_headers,
            json={
                "expectedVersion": version,
                "content": {
                    "reason": "Diabetes follow-up (pytest).",
                    "objective": "A1C elevated; fasting glucose high.",
                    "recommendations": "Titrate metformin; adherence counseling.",
                },
                "diagnoses": [{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
                "routedToId": GERARDO_ID,
            },
        )
        assert patch.status_code == 200, patch.text
        version = patch.json()["version"]

        sign = await client.post(
            f"/api/v1/notes/{note_id}/sign",
            headers=s_headers,
            json={"expectedVersion": version},
        )
        assert sign.status_code == 200, sign.text
        assert sign.json()["status"] == "pending_review"
        version = sign.json()["version"]

        # --- Instructor: cosign ---
        instructor = await _mfa_login(client, GERARDO)
        i_headers = {"Authorization": f"Bearer {instructor['access_token']}"}

        cosign = await client.post(
            f"/api/v1/notes/{note_id}/cosign",
            headers=i_headers,
            json={"expectedVersion": version, "comment": "Looks good — approved."},
        )
        assert cosign.status_code == 200, cosign.text
        assert cosign.json()["status"] == "cosigned"
        assert cosign.json()["cosignedByName"]

        # --- Second note: return for revision ---
        create2 = await client.post(
            "/api/v1/notes",
            headers=s_headers,
            json={
                "patientId": AE_DANIEL,
                "templateId": "pharmacy_mtm",
                "discipline": "pharmacy",
            },
        )
        assert create2.status_code == 201
        n2 = create2.json()
        p2 = await client.patch(
            f"/api/v1/notes/{n2['id']}",
            headers=s_headers,
            json={
                "expectedVersion": n2["version"],
                "content": {"reason": "Incomplete draft for return path."},
                "routedToId": GERARDO_ID,
            },
        )
        assert p2.status_code == 200
        s2 = await client.post(
            f"/api/v1/notes/{n2['id']}/sign",
            headers=s_headers,
            json={"expectedVersion": p2.json()["version"]},
        )
        assert s2.status_code == 200
        assert s2.json()["status"] == "pending_review"

        returned = await client.post(
            f"/api/v1/notes/{n2['id']}/return",
            headers=i_headers,
            json={
                "expectedVersion": s2.json()["version"],
                "comment": "Please expand the assessment and plan sections.",
            },
        )
        assert returned.status_code == 200, returned.text
        body = returned.json()
        assert body["status"] == "returned"
        assert any(f.get("kind") == "returned" for f in body.get("feedback") or [])
