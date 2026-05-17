from models import User, db


def _make_user(name, email):
    u = User(username=name, email=email)
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


def test_search_excludes_existing_friends(auth_client, user):
    bob = _make_user("bobby", "bobby@example.com")
    charlie = _make_user("bobsalad", "bsal@example.com")
    user.friends.append(bob)
    db.session.commit()

    resp = auth_client.get("/api/users/search?q=bob")
    data = resp.get_json()
    usernames = {u["username"] for u in data}
    assert "bobsalad" in usernames
    assert "bobby" not in usernames


def test_search_still_returns_non_friends(auth_client, user):
    _make_user("bob", "bob@example.com")
    resp = auth_client.get("/api/users/search?q=bob")
    usernames = {u["username"] for u in resp.get_json()}
    assert "bob" in usernames


def test_search_still_excludes_self(auth_client, user):
    resp = auth_client.get("/api/users/search?q=alice")
    usernames = {u["username"] for u in resp.get_json()}
    assert "alice" not in usernames
