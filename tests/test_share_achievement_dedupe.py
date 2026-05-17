"""Achievement-share dedupe by achievement_key, not by content string."""
from datetime import date

from achievements import award_achievements
from models import Exercise, FeedPost, db


def _earn_first_workout(user_id):
    db.session.add(Exercise(
        user_id=user_id, type="Running", date=date.today(),
        duration=30, intensity="Medium",
    ))
    db.session.commit()
    award_achievements(user_id)


def test_first_share_creates_a_post_tagged_with_key(auth_client, user):
    _earn_first_workout(user.id)
    resp = auth_client.post("/achievements/first_workout/share")
    assert resp.status_code == 200
    post = FeedPost.query.filter_by(user_id=user.id, post_type="achievement").one()
    assert post.achievement_key == "first_workout"


def test_second_share_is_rejected_even_if_content_string_changed(auth_client, user):
    _earn_first_workout(user.id)
    auth_client.post("/achievements/first_workout/share")
    # Simulate someone editing the achievement's display content — the dedup
    # should still trigger because we match on achievement_key now.
    post = FeedPost.query.filter_by(achievement_key="first_workout").one()
    post.content = "totally different content"
    db.session.commit()

    resp = auth_client.post("/achievements/first_workout/share")
    assert resp.status_code == 400
    assert FeedPost.query.filter_by(achievement_key="first_workout").count() == 1
