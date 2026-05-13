import os
import sys
import tempfile

import pytest

# Point the app at a throwaway DB before importing it so the dev DB is never touched.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app as flask_app  # noqa: E402
from models import User, db  # noqa: E402


@pytest.fixture
def app():
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{_db_path}",
    )
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(username="alice", email="alice@example.com")
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    client.post(
        "/login",
        data={"identifier": "alice", "password": "password123"},
        follow_redirects=False,
    )
    return client
