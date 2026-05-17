from datetime import date, datetime, timedelta

from models import Exercise, FeedPost, Goal, db


def _make_goal(user, goal_type, target, created_offset_days=0):
    """Create a goal whose creation date is offset_days in the past."""
    g = Goal(
        user_id=user.id, goal_type=goal_type, target_value=target,
        deadline=date.today() + timedelta(days=30),
    )
    db.session.add(g)
    db.session.commit()
    if created_offset_days:
        g.created_at = datetime.utcnow() - timedelta(days=created_offset_days)
        db.session.commit()
    return g


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


# --- Goal progress (regression for stuck-at-0% bug) ---

def test_distance_goal_progress_sums_exercise_distance(app, user):
    g = _make_goal(user, "Distance (km)", target=20.0, created_offset_days=2)
    db.session.add_all([
        Exercise(user_id=user.id, type="Running", date=date.today(),
                 duration=30, intensity="Medium", distance=5.0),
        Exercise(user_id=user.id, type="Cycling", date=date.today(),
                 duration=60, intensity="High", distance=15.0),
    ])
    db.session.commit()

    assert g.computed_current == 20.0
    assert g.progress_pct == 100
    assert g.is_completed_now is True


def test_duration_goal_progress_sums_exercise_minutes(app, user):
    g = _make_goal(user, "Total Duration (minutes)", target=100, created_offset_days=2)
    db.session.add_all([
        Exercise(user_id=user.id, type="Yoga", date=date.today(),
                 duration=45, intensity="Low"),
        Exercise(user_id=user.id, type="Running", date=date.today(),
                 duration=30, intensity="High"),
    ])
    db.session.commit()

    assert g.computed_current == 75
    assert g.progress_pct == 75
    assert g.is_completed_now is False


def test_frequency_goal_progress_counts_sessions(app, user):
    g = _make_goal(user, "Workout Frequency (sessions)", target=3, created_offset_days=2)
    for _ in range(2):
        db.session.add(Exercise(
            user_id=user.id, type="Walking", date=date.today(),
            duration=20, intensity="Low",
        ))
    db.session.commit()

    assert g.computed_current == 2
    assert g.display_current == 2
    assert g.progress_pct == 66


def test_exercises_logged_before_goal_creation_dont_count(app, user):
    # Goal created today; exercise dated yesterday is outside the window.
    g = _make_goal(user, "Distance (km)", target=10.0)
    db.session.add(Exercise(
        user_id=user.id, type="Running", date=date.today() - timedelta(days=1),
        duration=30, intensity="Medium", distance=5.0,
    ))
    db.session.commit()

    assert g.computed_current == 0.0
    assert g.progress_pct == 0


def test_dashboard_lists_completed_goals_separately(auth_client, user):
    # One goal that's done, one that isn't — only the active one shows on dashboard.
    active = _make_goal(user, "Distance (km)", target=100.0, created_offset_days=2)
    done   = _make_goal(user, "Workout Frequency (sessions)", target=1, created_offset_days=2)
    db.session.add(Exercise(
        user_id=user.id, type="Running", date=date.today(),
        duration=30, intensity="Medium", distance=5.0,
    ))
    db.session.commit()

    resp = auth_client.get("/goals")
    body = resp.get_data(as_text=True)
    # Active goal renders with its goal_type label; completed goal goes to the
    # "Completed Goals" section.
    assert "Distance (km)" in body
    # The completed goal appears in the Completed Goals section (which uses 🏆).
    assert "🏆" in body
    assert done.is_completed_now
    assert not active.is_completed_now
