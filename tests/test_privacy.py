from models import User, UserSettings, db


def _make_user(username, email, password="password123", privacy="public"):
    u = User(username=username, email=email)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    db.session.add(UserSettings(user_id=u.id, privacy=privacy))
    db.session.commit()
    return u


def test_private_blocks_even_friends(auth_client, user):
    bob = _make_user("bob", "bob@example.com", privacy="private")
    db.session.get(User, user.id).friends.append(bob)
    db.session.commit()

    resp = auth_client.get("/users/bob", follow_redirects=False)
    assert resp.status_code == 302
    assert "/social" in resp.headers["Location"]


def test_friends_only_allows_friends(auth_client, user):
    bob = _make_user("bob", "bob@example.com", privacy="friends")
    db.session.get(User, user.id).friends.append(bob)
    db.session.commit()

    resp = auth_client.get("/users/bob")
    assert resp.status_code == 200


def test_friends_only_blocks_non_friends(auth_client, user):
    _make_user("bob", "bob@example.com", privacy="friends")
    resp = auth_client.get("/users/bob", follow_redirects=False)
    assert resp.status_code == 302
    assert "/social" in resp.headers["Location"]


def test_public_visible_to_anyone(auth_client, user):
    _make_user("charlie", "charlie@example.com", privacy="public")
    resp = auth_client.get("/users/charlie")
    assert resp.status_code == 200
