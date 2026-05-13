from models import User, db


def test_signup_creates_user_with_hashed_password(client, app):
    resp = client.post(
        "/signup",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password": "supersecret",
            "password_confirm": "supersecret",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    user = User.query.filter_by(username="bob").one()
    assert user.password_hash != "supersecret"
    assert user.check_password("supersecret")


def test_login_with_valid_credentials_redirects_to_dashboard(client, user):
    resp = client.post(
        "/login",
        data={"identifier": "alice", "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


def test_login_with_wrong_password_stays_on_login(client, user):
    resp = client.post(
        "/login",
        data={"identifier": "alice", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert b"Invalid username/email or password" in resp.data
