"""End-to-end Selenium tests against a live Flask server.

Each test:
  * uses the function-scoped `app` fixture (resets the SQLite tables)
  * hits the live server provided by the session-scoped `live_server_url` fixture
  * drives a headless Chrome browser via the `browser` fixture
"""
import time
from datetime import date, timedelta

import pytest

pytest.importorskip("selenium")

from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import Select, WebDriverWait  # noqa: E402

from models import Exercise, Goal, db  # noqa: E402


def _login(browser, base_url, identifier="alice", password="password123"):
    browser.get(f"{base_url}/login")
    browser.find_element(By.ID, "identifier").send_keys(identifier)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.ID, "submit").click()
    WebDriverWait(browser, 10).until(lambda d: "/login" not in d.current_url)


def test_signup_creates_account_and_lands_on_dashboard(app, live_server_url, browser):
    browser.get(f"{live_server_url}/signup")
    browser.find_element(By.ID, "username").send_keys("charlie")
    browser.find_element(By.ID, "email").send_keys("charlie@example.com")
    browser.find_element(By.ID, "password").send_keys("supersecret")
    browser.find_element(By.ID, "password_confirm").send_keys("supersecret")
    browser.find_element(By.ID, "submit").click()

    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Hey, charlie')]"))
    )
    assert "/login" not in browser.current_url


def test_login_with_invalid_password_shows_error(app, user, live_server_url, browser):
    browser.get(f"{live_server_url}/login")
    browser.find_element(By.ID, "identifier").send_keys("alice")
    browser.find_element(By.ID, "password").send_keys("wrong-password")
    browser.find_element(By.ID, "submit").click()

    WebDriverWait(browser, 10).until(
        EC.text_to_be_present_in_element(
            (By.TAG_NAME, "body"), "Invalid username/email or password"
        )
    )


def test_log_exercise_appears_in_history(app, user, live_server_url, browser):
    _login(browser, live_server_url)
    browser.get(f"{live_server_url}/log")

    Select(browser.find_element(By.ID, "type")).select_by_visible_text("Running")
    # Setting <input type="date"> via send_keys is brittle in headless Chrome;
    # set the value explicitly so it doesn't depend on locale or auto-fill JS timing.
    browser.execute_script(
        "document.getElementById('date').value = arguments[0];",
        date.today().isoformat(),
    )
    duration = browser.find_element(By.ID, "duration")
    duration.clear()
    duration.send_keys("42")
    Select(browser.find_element(By.ID, "intensity")).select_by_visible_text("Medium")
    browser.find_element(By.CSS_SELECTOR, "#logForm button[type='submit']").click()

    WebDriverWait(browser, 10).until(EC.url_contains("/history"))
    body = browser.find_element(By.TAG_NAME, "body").text
    assert "Running" in body
    assert "42 min" in body


def test_dashboard_shows_logged_workout_count(app, user, live_server_url, browser):
    today = date.today()
    with app.app_context():
        db.session.add(Exercise(
            user_id=user.id, type="Cycling", date=today,
            duration=30, intensity="High",
        ))
        db.session.add(Exercise(
            user_id=user.id, type="Yoga", date=today - timedelta(days=1),
            duration=45, intensity="Low",
        ))
        db.session.commit()

    _login(browser, live_server_url)
    browser.get(f"{live_server_url}/")

    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Hey, alice')]"))
    )
    body = browser.find_element(By.TAG_NAME, "body").text
    assert "Workouts this week" in body
    assert "Cycling" in body
    assert "Yoga" in body


def test_goal_can_be_created_via_ajax_form(app, user, live_server_url, browser):
    _login(browser, live_server_url)
    browser.get(f"{live_server_url}/goals")

    Select(browser.find_element(By.NAME, "goal_type")).select_by_visible_text(
        "Distance (km)"
    )
    browser.execute_script(
        "document.getElementById('deadline').value = arguments[0];",
        (date.today() + timedelta(days=30)).isoformat(),
    )
    target = browser.find_element(By.NAME, "target_value")
    target.clear()
    target.send_keys("25")
    browser.find_element(By.CSS_SELECTOR, "#goalForm button[type='submit']").click()

    # AJAX submit, then JS reloads the page after ~800ms. Poll the DB directly —
    # the form's <option> text is already in the DOM, so we can't rely on a
    # text-presence check to detect success.
    deadline_ts = time.monotonic() + 10
    while time.monotonic() < deadline_ts:
        with app.app_context():
            if Goal.query.filter_by(user_id=user.id).count() == 1:
                break
        time.sleep(0.2)
    else:
        pytest.fail("Goal was not persisted within the timeout window")

    with app.app_context():
        goal = Goal.query.filter_by(user_id=user.id).one()
        assert goal.target_value == 25.0
        assert goal.goal_type == "Distance (km)"


def test_sidebar_navigation_to_profile_page(app, user, live_server_url, browser):
    _login(browser, live_server_url)
    browser.get(f"{live_server_url}/")

    profile_link = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//aside//a[contains(., 'Profile')]"))
    )
    profile_link.click()

    WebDriverWait(browser, 10).until(EC.url_contains("/profile"))
    body = browser.find_element(By.TAG_NAME, "body").text
    assert "alice" in body


def test_clicking_friend_in_profile_opens_their_profile(app, user, live_server_url, browser):
    from models import User, UserSettings, db
    # Set up a friend with a public profile.
    with app.app_context():
        bob = User(username="bob_e2e", email="bob_e2e@example.com")
        bob.set_password("password123")
        db.session.add(bob)
        db.session.commit()
        db.session.add(UserSettings(user_id=bob.id, privacy="public"))
        u = db.session.get(User, user.id)
        u.friends.append(bob)
        db.session.commit()

    _login(browser, live_server_url)
    browser.get(f"{live_server_url}/profile")

    friend_link = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/users/bob_e2e')]"))
    )
    friend_link.click()

    WebDriverWait(browser, 10).until(EC.url_contains("/users/bob_e2e"))
    body = browser.find_element(By.TAG_NAME, "body").text
    assert "bob_e2e" in body
    assert "Achievements" in body
