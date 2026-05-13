from datetime import date

from models import Exercise, User, db


def test_log_exercise_creates_row(auth_client, user):
    resp = auth_client.post(
        "/log",
        data={
            "type": "Running",
            "date": "2026-05-10",
            "duration": "30",
            "intensity": "Medium",
            "distance": "5.0",
            "notes": "felt good",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    ex = Exercise.query.filter_by(user_id=user.id).one()
    assert ex.type == "Running"
    assert ex.duration == 30
    assert ex.distance == 5.0
    assert ex.date == date(2026, 5, 10)


def test_delete_exercise_only_works_for_owner(client, app, user):
    # Alice's workout
    ex = Exercise(
        user_id=user.id, type="Cycling", date=date(2026, 5, 1),
        duration=60, intensity="High",
    )
    db.session.add(ex)
    # A second user logs in and tries to delete Alice's record
    eve = User(username="eve", email="eve@example.com")
    eve.set_password("password123")
    db.session.add(eve)
    db.session.commit()
    ex_id = ex.id

    client.post("/login", data={"identifier": "eve", "password": "password123"})
    client.post(f"/history/{ex_id}/delete")

    # Still there — eve isn't the owner
    assert db.session.get(Exercise, ex_id) is not None


def test_edit_exercise_updates_fields(auth_client, user):
    ex = Exercise(
        user_id=user.id, type="Yoga", date=date(2026, 5, 1),
        duration=45, intensity="Low",
    )
    db.session.add(ex)
    db.session.commit()

    resp = auth_client.post(
        f"/history/{ex.id}/edit",
        data={
            "type": "Yoga",
            "date": "2026-05-02",
            "duration": "60",
            "intensity": "Medium",
            "distance": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    updated = db.session.get(Exercise, ex.id)
    assert updated.duration == 60
    assert updated.intensity == "Medium"
    assert updated.date == date(2026, 5, 2)
