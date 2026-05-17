from models import db


def _post_settings(client, **overrides):
    base = dict(
        username="alice", email="alice@example.com",
        first_name="", last_name="", bio="",
        privacy="public", reminder_time="07:30",
    )
    base.update(overrides)
    return client.post("/settings", data=base, follow_redirects=False)


def test_bio_can_be_set_via_settings(auth_client, user):
    resp = _post_settings(auth_client, bio="Marathon runner. Coffee enthusiast.")
    assert resp.status_code == 302
    db.session.refresh(user)
    assert user.bio == "Marathon runner. Coffee enthusiast."


def test_bio_shows_on_profile_after_set(auth_client, user):
    _post_settings(auth_client, bio="I love yoga at 6am")
    resp = auth_client.get("/profile")
    assert b"I love yoga at 6am" in resp.data
    assert b"About" in resp.data


def test_blank_bio_clears_to_none(auth_client, user):
    _post_settings(auth_client, bio="something")
    db.session.refresh(user)
    assert user.bio == "something"
    _post_settings(auth_client, bio="")
    db.session.refresh(user)
    assert user.bio is None
