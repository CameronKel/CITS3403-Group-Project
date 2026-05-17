from datetime import date, datetime, timedelta

from achievements import award_achievements, status_for_user
from models import Exercise, FeedPost, Goal, UserAchievement, db


def _log(user_id, **kwargs):
    defaults = dict(
        user_id=user_id, type="Running", date=date.today(),
        duration=30, intensity="Medium", distance=5.0,
    )
    defaults.update(kwargs)
    db.session.add(Exercise(**defaults))


def test_first_workout_awarded_after_one_exercise(app, user):
    _log(user.id)
    db.session.commit()

    keys = award_achievements(user.id)
    assert "first_workout" in keys
    assert UserAchievement.query.filter_by(
        user_id=user.id, achievement_key="first_workout"
    ).count() == 1


def test_award_is_idempotent(app, user):
    _log(user.id)
    db.session.commit()
    award_achievements(user.id)
    # Running it again should not duplicate.
    second_round = award_achievements(user.id)
    assert "first_workout" not in second_round
    assert UserAchievement.query.filter_by(
        user_id=user.id, achievement_key="first_workout"
    ).count() == 1


def test_distance_demon_requires_50km_total(app, user):
    # 49km — not enough
    _log(user.id, distance=25.0)
    _log(user.id, distance=24.0)
    db.session.commit()
    keys = award_achievements(user.id)
    assert "distance_demon" not in keys

    # Top it up to 50km
    _log(user.id, distance=1.0)
    db.session.commit()
    keys = award_achievements(user.id)
    assert "distance_demon" in keys


def test_variety_pack_needs_5_distinct_types(app, user):
    for t in ["Running", "Cycling", "Swimming", "Yoga"]:
        _log(user.id, type=t)
    db.session.commit()
    keys = award_achievements(user.id)
    assert "variety_pack" not in keys

    _log(user.id, type="Walking")
    db.session.commit()
    keys = award_achievements(user.id)
    assert "variety_pack" in keys


def test_iron_will_needs_5_high_intensity(app, user):
    for _ in range(5):
        _log(user.id, intensity="High")
    db.session.commit()
    keys = award_achievements(user.id)
    assert "iron_will" in keys


def test_marathon_session_needs_60_minute_workout(app, user):
    _log(user.id, duration=45)
    db.session.commit()
    assert "marathon_session" not in award_achievements(user.id)

    _log(user.id, duration=60)
    db.session.commit()
    assert "marathon_session" in award_achievements(user.id)


def test_goal_getter_awarded_when_a_goal_is_completed(app, user):
    g = Goal(
        user_id=user.id, goal_type="Distance (km)", target_value=5.0,
        deadline=date.today() + timedelta(days=30),
    )
    db.session.add(g)
    db.session.commit()
    g.created_at = datetime.utcnow() - timedelta(days=1)
    db.session.commit()

    _log(user.id, distance=5.0)
    db.session.commit()

    assert g.is_completed_now
    keys = award_achievements(user.id)
    assert "goal_getter" in keys


def test_log_exercise_route_awards_first_workout(auth_client, user):
    resp = auth_client.post("/log", data={
        "type": "Running", "date": date.today().isoformat(),
        "duration": "30", "intensity": "Medium", "distance": "5.0",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert UserAchievement.query.filter_by(
        user_id=user.id, achievement_key="first_workout"
    ).count() == 1


def test_status_for_user_returns_progress_for_all_achievements(app, user):
    _log(user.id, distance=10.0)
    db.session.commit()
    status = status_for_user(user.id)
    by_key = {a.key: (earned, current, target) for a, earned, current, target in status}
    assert by_key["distance_demon"] == (None, 10, 50)
    # first_workout reaches its target but hasn't been awarded yet (we haven't
    # called award_achievements), so earned_at is None but current >= target.
    assert by_key["first_workout"][1] >= by_key["first_workout"][2]


def test_share_earned_achievement_creates_feed_post(auth_client, user):
    _log(user.id)
    db.session.commit()
    award_achievements(user.id)

    resp = auth_client.post("/achievements/first_workout/share")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "shared"
    post = FeedPost.query.filter_by(user_id=user.id, post_type="achievement").one()
    assert "First Steps" in post.content


def test_sharing_unearned_achievement_is_forbidden(auth_client, user):
    resp = auth_client.post("/achievements/first_workout/share")
    assert resp.status_code == 403
    assert FeedPost.query.filter_by(post_type="achievement").count() == 0


def test_sharing_unknown_achievement_returns_404(auth_client, user):
    resp = auth_client.post("/achievements/not_a_real_key/share")
    assert resp.status_code == 404
