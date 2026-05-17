from models import User, db


def _post_settings(client, **overrides):
    base = dict(
        username="alice", email="alice@example.com",
        first_name="", last_name="", bio="",
        privacy="public", reminder_time="07:30",
    )
    base.update(overrides)
    return client.post("/settings", data=base, follow_redirects=True)


def _make_user(name, email):
    u = User(username=name, email=email)
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


def test_username_conflict_flashes_error_and_keeps_old_value(auth_client, user):
    _make_user("bob", "bob@example.com")
    resp = _post_settings(auth_client, username="bob")
    assert b"already taken" in resp.data
    db.session.refresh(user)
    assert user.username == "alice"


def test_email_conflict_flashes_error_and_keeps_old_value(auth_client, user):
    _make_user("bob", "bob@example.com")
    resp = _post_settings(auth_client, email="bob@example.com")
    assert b"already in use" in resp.data
    db.session.refresh(user)
    assert user.email == "alice@example.com"


def test_clean_username_change_still_works(auth_client, user):
    resp = _post_settings(auth_client, username="alice2")
    assert b"Settings saved" in resp.data
    db.session.refresh(user)
    assert user.username == "alice2"
