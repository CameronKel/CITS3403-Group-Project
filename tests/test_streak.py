from datetime import date, timedelta

from models import Exercise, db


def _log(user_id, on_date, **kwargs):
    base = dict(type="Running", duration=30, intensity="Medium")
    base.update(kwargs)
    db.session.add(Exercise(user_id=user_id, date=on_date, **base))


def test_streak_counts_consecutive_days_ending_today(app, user):
    today = date.today()
    for offset in range(5):
        _log(user.id, today - timedelta(days=offset))
    db.session.commit()
    assert user.compute_streak(today) == 5


def test_streak_resets_when_today_is_skipped(app, user):
    today = date.today()
    # Logged yesterday and the day before, but not today.
    _log(user.id, today - timedelta(days=1))
    _log(user.id, today - timedelta(days=2))
    db.session.commit()
    assert user.compute_streak(today) == 0


def test_streak_stops_at_first_gap(app, user):
    today = date.today()
    _log(user.id, today)
    _log(user.id, today - timedelta(days=1))
    # gap on day -2
    _log(user.id, today - timedelta(days=3))
    db.session.commit()
    assert user.compute_streak(today) == 2


def test_dashboard_does_not_persist_streak_to_db(auth_client, user):
    today = date.today()
    _log(user.id, today)
    db.session.commit()
    # `streak` column shouldn't be written by the dashboard GET. We can't
    # observe a no-write directly, but we can confirm the streak column is
    # not touched by checking it stays at its default (0) after a GET.
    assert user.streak == 0
    auth_client.get("/")
    db.session.refresh(user)
    assert user.streak == 0


def test_profile_shows_fresh_streak_without_dashboard_roundtrip(auth_client, user):
    today = date.today()
    _log(user.id, today)
    db.session.commit()
    resp = auth_client.get("/profile")
    # Stat card label
    assert b"Day streak" in resp.data
    # The freshly-computed value (1) should appear in the rendered HTML.
    assert b">1<" in resp.data or b"> 1 <" in resp.data
