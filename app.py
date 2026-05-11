import os

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_migrate import Migrate
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect

from forms import LoginForm, SignupForm
from datetime import date
from models import Exercise, FeedPost, Goal, User, UserSettings, db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Auth ---

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("signup.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.identifier.data.strip()
        user = User.query.filter(
            (User.username == ident) | (User.email == ident.lower())
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid username/email or password.", "error")
    return render_template("login.html", form=form)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# --- App pages (login required) ---

@app.route("/")
@login_required
def dashboard():
    from datetime import timedelta
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    week_exercises  = Exercise.query.filter(
        Exercise.user_id == current_user.id,
        Exercise.date >= week_start
    ).all()
    month_exercises = Exercise.query.filter(
        Exercise.user_id == current_user.id,
        Exercise.date >= month_start
    ).all()

    week_count   = len(week_exercises)
    week_minutes = sum(e.duration for e in week_exercises)
    month_minutes = sum(e.duration for e in month_exercises)
    active_goal  = Goal.query.filter_by(user_id=current_user.id, completed=False).first()
    recent       = (Exercise.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Exercise.date.desc())
                    .limit(5).all())

    return render_template("dashboard.html", active_page="dashboard",
        week_count=week_count, week_minutes=week_minutes, month_minutes=month_minutes,
        active_goal=active_goal, recent=recent)


@app.route("/log", methods=["GET", "POST"])
@login_required
def log_exercise():
    if request.method == "POST":
        exercise = Exercise(
            user_id   = current_user.id,
            type      = request.form["type"],
            date      = date.fromisoformat(request.form["date"]),
            duration  = int(request.form["duration"]),
            intensity = request.form["intensity"],
            distance  = float(request.form["distance"]) if request.form.get("distance") else None,
            notes     = request.form.get("notes") or None,
        )
        db.session.add(exercise)
        db.session.commit()
        flash("Workout saved!", "success")
        return redirect(url_for("history"))
    return render_template("log_exercise.html", active_page="log_exercise")


@app.route("/history")
@login_required
def history():
    exercises = (Exercise.query
                 .filter_by(user_id=current_user.id)
                 .order_by(Exercise.date.desc())
                 .all())
    return render_template("history.html", active_page="history", exercises=exercises)

@app.route("/history/<int:id>/delete", methods=["POST"])
@login_required
def delete_exercise(id):
    exercise = db.session.get(Exercise, id)
    if exercise and exercise.user_id == current_user.id:
        db.session.delete(exercise)
        db.session.commit()
        flash("Workout deleted.", "success")
    return redirect(url_for("history"))

@app.route("/history/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_exercise(id):
    exercise = db.session.get(Exercise, id)
    if not exercise or exercise.user_id != current_user.id:
        flash("Workout not found.", "error")
        return redirect(url_for("history"))
    if request.method == "POST":
        exercise.type      = request.form["type"]
        exercise.date      = date.fromisoformat(request.form["date"])
        exercise.duration  = int(request.form["duration"])
        exercise.intensity = request.form["intensity"]
        exercise.distance  = float(request.form["distance"]) if request.form.get("distance") else None
        exercise.notes     = request.form.get("notes") or None
        db.session.commit()
        flash("Workout updated!", "success")
        return redirect(url_for("history"))
    return render_template("edit_exercise.html", active_page="history", exercise=exercise)


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "POST":
        goal = Goal(
            user_id      = current_user.id,
            goal_type    = request.form["goal_type"],
            target_value = float(request.form["target_value"]),
            deadline     = date.fromisoformat(request.form["deadline"]),
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({"status": "ok", "id": goal.id})   # AJAX response
    active_goals    = Goal.query.filter_by(user_id=current_user.id, completed=False).all()
    completed_goals = Goal.query.filter_by(user_id=current_user.id, completed=True).all()
    return render_template("goals.html", active_page="goals",
                           active_goals=active_goals, completed_goals=completed_goals)


@app.route("/goals/<int:id>/share", methods=["POST"])
@login_required
def share_goal(id):
    goal = db.session.get(Goal, id)
    if not goal or goal.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    post = FeedPost(
        user_id   = current_user.id,
        post_type = "goal",
        content   = f"Completed goal: {goal.goal_type} — target {goal.target_value}",
        goal_id   = goal.id,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"status": "shared"})

@app.route("/social")
@login_required
def social():
    friend_ids = [f.id for f in current_user.friends]
    posts = (FeedPost.query
             .filter(FeedPost.user_id.in_(friend_ids + [current_user.id]))
             .order_by(FeedPost.created_at.desc())
             .limit(20).all())
    return render_template("social.html", active_page="social", posts=posts)


@app.route("/profile")
@login_required
def profile():
    total_workouts  = Exercise.query.filter_by(user_id=current_user.id).count()
    total_distance  = db.session.query(db.func.sum(Exercise.distance)) \
                        .filter_by(user_id=current_user.id).scalar() or 0
    completed_goals = Goal.query.filter_by(user_id=current_user.id, completed=True).count()
    return render_template("profile.html", active_page="profile",
        total_workouts=total_workouts,
        total_distance=round(total_distance, 1),
        completed_goals=completed_goals)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    s = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not s:
        s = UserSettings(user_id=current_user.id)
        db.session.add(s)
        db.session.commit()
    if request.method == "POST":
        s.workout_reminders = "workout_reminders" in request.form
        s.goal_alerts       = "goal_alerts"       in request.form
        s.friend_activity   = "friend_activity"   in request.form
        s.streak_warnings   = "streak_warnings"   in request.form
        s.weekly_summary    = "weekly_summary"     in request.form
        s.training_days     = ",".join(request.form.getlist("training_days"))
        s.reminder_time     = request.form.get("reminder_time", "07:30")
        s.privacy           = request.form.get("privacy", "public")
        db.session.commit()
        flash("Settings saved!", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", active_page="settings", s=s)


def init_db() -> None:
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
