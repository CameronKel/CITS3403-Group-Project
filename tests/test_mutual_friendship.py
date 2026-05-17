from datetime import date

from models import FeedPost, User, db


def test_adding_a_friend_is_symmetric(auth_client, user):
    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()

    auth_client.post(f"/api/friends/add/{bob.id}")

    assert bob in user.friends
    assert user in bob.friends


def test_bob_sees_alices_posts_after_alice_friends_him(auth_client, user, client):
    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()
    db.session.add(FeedPost(user_id=user.id, post_type="goal", content="Did a thing"))
    db.session.commit()

    # Alice friends Bob.
    auth_client.post(f"/api/friends/add/{bob.id}")

    # Bob now logs in and visits social — should see Alice's post.
    client.post("/login", data={"identifier": "bob", "password": "password123"})
    resp = client.get("/social")
    assert b"Did a thing" in resp.data


def test_adding_self_is_a_noop(auth_client, user):
    before = len(user.friends)
    auth_client.post(f"/api/friends/add/{user.id}")
    assert len(user.friends) == before


def test_adding_twice_is_idempotent(auth_client, user):
    bob = User(username="bob", email="bob@example.com")
    bob.set_password("password123")
    db.session.add(bob)
    db.session.commit()

    auth_client.post(f"/api/friends/add/{bob.id}")
    auth_client.post(f"/api/friends/add/{bob.id}")

    assert user.friends.count(bob) == 1
    assert bob.friends.count(user) == 1
