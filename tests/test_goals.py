from datetime import date

from models import FeedPost, Goal, db


def test_create_goal_via_post_returns_json_and_persists(auth_client, user):
    resp = auth_client.post(
        "/goals",
        data={
            "goal_type": "weekly_minutes",
            "target_value": "150",
            "deadline": "2026-12-31",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    goal = db.session.get(Goal, body["id"])
    assert goal is not None
    assert goal.user_id == user.id
    assert goal.target_value == 150.0


def test_share_goal_creates_feed_post(auth_client, user):
    goal = Goal(
        user_id=user.id, goal_type="weekly_minutes",
        target_value=150, deadline=date(2026, 12, 31),
    )
    db.session.add(goal)
    db.session.commit()

    resp = auth_client.post(f"/goals/{goal.id}/share")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "shared"
    post = FeedPost.query.filter_by(goal_id=goal.id).one()
    assert post.user_id == user.id
    assert post.post_type == "goal"
