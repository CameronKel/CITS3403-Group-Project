# CITS3403 Group Project

Exercise tracking web app — users log workouts, view stats, set goals, and share achievements with friends.

## Tech

- Flask + Jinja templates
- Tailwind (via CDN), jQuery, Chart.js, Font Awesome — all CDN-loaded

## Project layout

```
app.py              # Flask routes
templates/          # Jinja templates
  base.html         # shared layout (head, sidebar, mobile bar)
  dashboard.html    # extends base
  log_exercise.html
  history.html
  edit_exercise.html
  goals.html
  social.html
  profile.html
  settings.html
requirements.txt
```

Each page template extends `base.html` and overrides the `title`, `extra_head`, `content`, and `extra_scripts` blocks. The active sidebar item is set by the `active_page` variable passed from the route.

## Run

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000.
