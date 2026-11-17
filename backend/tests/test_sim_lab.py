"""Sim Center lab check-in."""

from datetime import date

import pytest

from tests.test_workflows import course_id, login


@pytest.mark.asyncio
async def test_instructor_assigns_student_sees_mine_and_clear(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, student_body = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    today = date.today().isoformat()
    student_id = student_body["user"]["id"]

    rooms = await client.get(
        f"/api/v1/courses/{course}/sim-lab/rooms",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert rooms.status_code == 200, rooms.text
    catalog = rooms.json()
    assert any(r["number"] == "109" for r in catalog)
    assert any(r["number"] == "126" and r["bedCount"] == 10 for r in catalog)
    room_109 = next(r for r in catalog if r["number"] == "109")
    assert room_109["bedOptions"] == ["A", "B", "C", "D", "E"]
    assert room_109["softCapacity"] == 25

    denied_board = await client.get(
        f"/api/v1/courses/{course}/sim-lab/assignments",
        headers=student,
        params={"role": "student", "session_date": today},
    )
    assert denied_board.status_code == 403

    assigned = await client.post(
        f"/api/v1/courses/{course}/sim-lab/assignments",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "userId": student_id,
            "roomId": room_109["id"],
            "sessionDate": today,
            "bed": "B",
            "roleLabel": "Nurse",
        },
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["room"]["number"] == "109"
    assert body["bed"] == "B"
    assert body["roleLabel"] == "Nurse"
    assert body["studentName"] == "Daniel Reyes"

    mine = await client.get(
        f"/api/v1/courses/{course}/sim-lab/mine",
        headers=student,
        params={"role": "student", "session_date": today},
    )
    assert mine.status_code == 200, mine.text
    assert len(mine.json()) == 1
    assert mine.json()[0]["room"]["number"] == "109"

    moved = await client.post(
        f"/api/v1/courses/{course}/sim-lab/assignments",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "userId": student_id,
            "roomId": next(r["id"] for r in catalog if r["number"] == "106"),
            "sessionDate": today,
            "timeBlock": "9:00–10:00",
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["room"]["number"] == "106"
    assert moved.json()["timeBlock"] == "9:00–10:00"
    assert moved.json()["id"] == body["id"]

    cleared = await client.post(
        f"/api/v1/courses/{course}/sim-lab/assignments/{body['id']}/clear",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert cleared.status_code == 200, cleared.text

    empty = await client.get(
        f"/api/v1/courses/{course}/sim-lab/mine",
        headers=student,
        params={"role": "student", "session_date": today},
    )
    assert empty.status_code == 200
    assert empty.json() == []
