"""Server-side validation for the exercise log/edit forms — disabling JS or
hitting the endpoint via curl shouldn't yield a 500."""
from datetime import date

from models import Exercise, db


def test_log_with_non_numeric_duration_returns_400ish_not_500(auth_client, user):
    resp = auth_client.post("/log", data={
        "type": "Running", "date": date.today().isoformat(),
        "duration": "abc", "intensity": "Medium",
    })
    assert resp.status_code in (200, 302, 400)
    assert resp.status_code != 500
    assert Exercise.query.filter_by(user_id=user.id).count() == 0


def test_log_with_bad_date_returns_400ish_not_500(auth_client, user):
    resp = auth_client.post("/log", data={
        "type": "Running", "date": "not-a-date",
        "duration": "30", "intensity": "Medium",
    })
    assert resp.status_code != 500
    assert Exercise.query.filter_by(user_id=user.id).count() == 0


def test_log_with_out_of_range_duration_is_rejected(auth_client, user):
    resp = auth_client.post("/log", data={
        "type": "Running", "date": date.today().isoformat(),
        "duration": "9999", "intensity": "Medium",
    })
    assert resp.status_code != 500
    assert Exercise.query.filter_by(user_id=user.id).count() == 0


def test_edit_with_bad_input_doesnt_crash(auth_client, user):
    ex = Exercise(
        user_id=user.id, type="Running", date=date.today(),
        duration=30, intensity="Medium",
    )
    db.session.add(ex)
    db.session.commit()

    resp = auth_client.post(f"/history/{ex.id}/edit", data={
        "type": "Running", "date": "not-a-date",
        "duration": "30", "intensity": "Medium",
    })
    assert resp.status_code != 500
    # Original record unchanged
    db.session.refresh(ex)
    assert ex.date == date.today()


def test_log_with_valid_input_still_works(auth_client, user):
    resp = auth_client.post("/log", data={
        "type": "Running", "date": date.today().isoformat(),
        "duration": "30", "intensity": "Medium", "distance": "5.0",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert Exercise.query.filter_by(user_id=user.id).count() == 1
