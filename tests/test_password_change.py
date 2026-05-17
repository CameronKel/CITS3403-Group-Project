from models import User, db


def _post_settings(client, **overrides):
    base = dict(
        username="alice", email="alice@example.com",
        first_name="", last_name="",
        privacy="public",
        reminder_time="07:30",
    )
    base.update(overrides)
    return client.post("/settings", data=base, follow_redirects=False)


def test_change_password_with_correct_current_works(auth_client, user):
    resp = _post_settings(auth_client,
        current_password="password123",
        new_password="brand-new-pw")
    assert resp.status_code == 302
    db.session.refresh(user)
    assert user.check_password("brand-new-pw")
    assert not user.check_password("password123")


def test_change_password_with_wrong_current_is_rejected(auth_client, user):
    _post_settings(auth_client,
        current_password="not-my-password",
        new_password="brand-new-pw")
    db.session.refresh(user)
    assert user.check_password("password123")
    assert not user.check_password("brand-new-pw")


def test_change_password_too_short_is_rejected(auth_client, user):
    _post_settings(auth_client,
        current_password="password123",
        new_password="short")
    db.session.refresh(user)
    assert user.check_password("password123")


def test_blank_new_password_leaves_password_unchanged(auth_client, user):
    # Saving other settings without touching password shouldn't reset it.
    _post_settings(auth_client, current_password="", new_password="")
    db.session.refresh(user)
    assert user.check_password("password123")
