from datetime import date, timedelta

from models import Goal


def test_past_deadline_is_rejected(auth_client, user):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = auth_client.post("/goals", data={
        "goal_type": "Distance (km)",
        "target_value": "10",
        "deadline": yesterday,
    })
    assert resp.status_code == 400
    assert "past" in resp.get_json()["error"].lower()
    assert Goal.query.filter_by(user_id=user.id).count() == 0


def test_today_deadline_is_allowed(auth_client, user):
    today = date.today().isoformat()
    resp = auth_client.post("/goals", data={
        "goal_type": "Distance (km)",
        "target_value": "10",
        "deadline": today,
    })
    assert resp.status_code == 200
    assert Goal.query.filter_by(user_id=user.id).count() == 1


def test_future_deadline_works_as_before(auth_client, user):
    future = (date.today() + timedelta(days=30)).isoformat()
    resp = auth_client.post("/goals", data={
        "goal_type": "Distance (km)",
        "target_value": "10",
        "deadline": future,
    })
    assert resp.status_code == 200
    assert Goal.query.filter_by(user_id=user.id).count() == 1


def test_invalid_deadline_string_returns_400(auth_client, user):
    resp = auth_client.post("/goals", data={
        "goal_type": "Distance (km)",
        "target_value": "10",
        "deadline": "not-a-date",
    })
    assert resp.status_code == 400
    assert Goal.query.filter_by(user_id=user.id).count() == 0
