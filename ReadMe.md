# CITS3403 Group Project

Exercise tracking web app — users log workouts, view stats, set goals, and share achievements with friends.

## Tech

- Flask + Jinja templates
- SQLite via Flask-SQLAlchemy
- Flask-Login for sessions, Flask-WTF for forms + CSRF
- Tailwind (via CDN), jQuery, Chart.js, Font Awesome — all CDN-loaded

## Project layout

```
app.py              # Flask routes + extension wiring
models.py           # SQLAlchemy models (User)
forms.py            # WTForms (LoginForm, SignupForm)
templates/
  base.html         # main app layout (sidebar)
  auth_base.html    # auth pages layout (centered card, no sidebar)
  login.html, signup.html
  dashboard.html, log_exercise.html, history.html,
  edit_exercise.html, goals.html, social.html,
  profile.html, settings.html
requirements.txt
.env.example        # copy to .env and set SECRET_KEY
```

App pages extend `base.html` and override `title`, `extra_head`, `content`, `extra_scripts`. The active sidebar item is set via the `active_page` variable. Auth pages extend `auth_base.html`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# One-time: copy env template and set a secret
cp .env.example .env
# then edit .env to set SECRET_KEY (e.g. python -c "import secrets; print(secrets.token_hex(32))")

python app.py
```

Open http://127.0.0.1:5000. The SQLite database is auto-created at `instance/app.db` on first start. Sign up to create an account, then log in.

## Auth notes

- Passwords are stored as salted hashes (werkzeug `generate_password_hash`).
- All forms include CSRF tokens (Flask-WTF). Logout uses a POST form with the same protection.
- All app pages require login; unauthenticated users are redirected to `/login`.
