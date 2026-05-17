from datetime import date

from models import Exercise, User, UserSettings, db


def _make_user(username, email, password="password123", privacy="public"):
    u = User(username=username, email=email)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    db.session.add(UserSettings(user_id=u.id, privacy=privacy))
    db.session.commit()
    return u


def test_viewing_a_friends_profile_shows_their_stats(auth_client, user):
    bob = _make_user("bob", "bob@example.com")
    current_user = db.session.get(User, user.id)
    current_user.friends.append(bob)
    db.session.add(Exercise(
        user_id=bob.id, type="Running", date=date.today(),
        duration=30, intensity="Medium", distance=5.0,
    ))
    db.session.commit()

    resp = auth_client.get("/users/bob")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "bob" in body
    assert "5.0 km" in body or "5 km" in body
    # Should show achievements section
    assert "Achievements" in body


def test_friend_profile_shows_earned_achievements(auth_client, user):
    bob = _make_user("bob", "bob@example.com")
    current_user = db.session.get(User, user.id)
    current_user.friends.append(bob)
    # Bob has logged a workout → should auto-award "First Steps" on profile view
    db.session.add(Exercise(
        user_id=bob.id, type="Running", date=date.today(),
        duration=30, intensity="Medium", distance=5.0,
    ))
    db.session.commit()

    resp = auth_client.get("/users/bob")
    body = resp.get_data(as_text=True)
    assert "First Steps" in body


def test_visiting_own_username_redirects_to_profile(auth_client, user):
    resp = auth_client.get(f"/users/{user.username}", follow_redirects=False)
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]


def test_private_non_friend_profile_is_blocked(auth_client, user):
    _make_user("eve", "eve@example.com", privacy="private")
    resp = auth_client.get("/users/eve", follow_redirects=False)
    assert resp.status_code == 302
    assert "/social" in resp.headers["Location"]


def test_public_non_friend_profile_is_visible(auth_client, user):
    _make_user("charlie", "charlie@example.com", privacy="public")
    resp = auth_client.get("/users/charlie")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "charlie" in body
    # Not friends — should show the Add friend button
    assert "Add friend" in body


def test_unknown_username_redirects_to_social(auth_client, user):
    resp = auth_client.get("/users/nonexistent", follow_redirects=False)
    assert resp.status_code == 302
    assert "/social" in resp.headers["Location"]


def test_friend_profile_shows_friends_badge(auth_client, user):
    bob = _make_user("bob", "bob@example.com")
    current_user = db.session.get(User, user.id)
    current_user.friends.append(bob)
    db.session.commit()

    resp = auth_client.get("/users/bob")
    body = resp.get_data(as_text=True)
    # The friends badge replaces the Add-friend button when already friends.
    assert "Friends" in body
    assert "Add friend" not in body
