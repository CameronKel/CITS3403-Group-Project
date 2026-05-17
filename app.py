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
from sqlalchemy import func

from forms import LoginForm, SignupForm
from datetime import date, datetime
from models import Exercise, FeedPost, Goal, User, UserAchievement, UserSettings, db
from achievements import award_achievements, status_for_user, BY_KEY

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
        ident_lower = ident.lower()
        user = User.query.filter(
            (func.lower(User.username) == ident_lower) | (User.email == ident_lower)
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
    active_goals  = [g for g in Goal.query.filter_by(user_id=current_user.id).all()
                     if not g.is_completed_now and not g.is_expired]
    recent       = (Exercise.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Exercise.date.desc())
                    .limit(5).all())

    streak = current_user.compute_streak(today)

    return render_template("dashboard.html", active_page="dashboard",
        week_count=week_count, week_minutes=week_minutes, month_minutes=month_minutes,
        active_goals=active_goals, recent=recent, now=datetime.now(), streak=streak)


def _parse_exercise_form(form):
    """Pull validated kwargs out of the exercise form. Raises ValueError on bad input."""
    try:
        kwargs = dict(
            type      = form["type"],
            date      = date.fromisoformat(form["date"]),
            duration  = int(form["duration"]),
            intensity = form["intensity"],
            distance  = float(form["distance"]) if form.get("distance") else None,
            notes     = form.get("notes") or None,
        )
    except (KeyError, ValueError, TypeError):
        raise ValueError("Please fill in all required fields with valid values.")
    if not kwargs["type"] or not kwargs["intensity"]:
        raise ValueError("Please fill in all required fields with valid values.")
    if kwargs["duration"] < 1 or kwargs["duration"] > 600:
        raise ValueError("Duration must be between 1 and 600 minutes.")
    return kwargs


@app.route("/log", methods=["GET", "POST"])
@login_required
def log_exercise():
    if request.method == "POST":
        try:
            kwargs = _parse_exercise_form(request.form)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("log_exercise.html", active_page="log_exercise")
        exercise = Exercise(user_id=current_user.id, **kwargs)
        db.session.add(exercise)
        db.session.commit()
        newly_earned = award_achievements(current_user.id)
        for key in newly_earned:
            a = BY_KEY.get(key)
            if a:
                flash(f"🏆 Achievement unlocked: {a.name}", "success")
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
        award_achievements(current_user.id)
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
        try:
            kwargs = _parse_exercise_form(request.form)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("edit_exercise.html", active_page="history", exercise=exercise)
        for k, v in kwargs.items():
            setattr(exercise, k, v)
        db.session.commit()
        newly_earned = award_achievements(current_user.id)
        for key in newly_earned:
            a = BY_KEY.get(key)
            if a:
                flash(f"🏆 Achievement unlocked: {a.name}", "success")
        flash("Workout updated!", "success")
        return redirect(url_for("history"))
    return render_template("edit_exercise.html", active_page="history", exercise=exercise)


@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "POST":
        try:
            deadline = date.fromisoformat(request.form["deadline"])
        except (KeyError, ValueError):
            return jsonify({"error": "Invalid deadline."}), 400
        if deadline < date.today():
            return jsonify({"error": "Deadline cannot be in the past."}), 400
        goal = Goal(
            user_id      = current_user.id,
            goal_type    = request.form["goal_type"],
            target_value = float(request.form["target_value"]),
            deadline     = deadline,
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({"status": "ok", "id": goal.id})   # AJAX response
    all_goals       = Goal.query.filter_by(user_id=current_user.id).all()
    active_goals    = [g for g in all_goals if not g.is_completed_now and not g.is_expired]
    completed_goals = [g for g in all_goals if g.is_completed_now]
    expired_goals   = [g for g in all_goals if g.is_expired]
    return render_template("goals.html", active_page="goals",
                           active_goals=active_goals,
                           completed_goals=completed_goals,
                           expired_goals=expired_goals)


@app.route("/goals/<int:id>/share", methods=["POST"])
@login_required
def share_goal(id):
    goal = db.session.get(Goal, id)
    if not goal or goal.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    already_shared = FeedPost.query.filter_by(
        user_id=current_user.id, post_type="goal", goal_id=goal.id
    ).first()
    if already_shared:
        return jsonify({"error": "Already shared"}), 400
    post = FeedPost(
        user_id   = current_user.id,
        post_type = "goal",
        content   = f"Completed goal: {goal.goal_type} — target {goal.target_value}",
        goal_id   = goal.id,
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({"status": "shared"})

@app.route("/achievements/<key>/share", methods=["POST"])
@login_required
def share_achievement(key):
    a = BY_KEY.get(key)
    if not a:
        return jsonify({"error": "Unknown achievement"}), 404
    earned = UserAchievement.query.filter_by(
        user_id=current_user.id, achievement_key=key
    ).first()
    if not earned:
        return jsonify({"error": "Not earned"}), 403
    already_shared = FeedPost.query.filter_by(
        user_id=current_user.id, post_type="achievement", content=f"{a.emoji} Unlocked achievement: {a.name} — {a.description}"
    ).first()
    if already_shared:
        return jsonify({"error": "Already shared"}), 400
    post = FeedPost(
        user_id=current_user.id,
        post_type="achievement",
        content=f"{a.emoji} Unlocked achievement: {a.name} — {a.description}",
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
    completed_goals = sum(1 for g in Goal.query.filter_by(user_id=current_user.id).all()
                          if g.is_completed_now)
    achievements_status = status_for_user(current_user.id)
    streak = current_user.compute_streak()
    return render_template("profile.html", active_page="profile",
        total_workouts=total_workouts,
        total_distance=round(total_distance, 1),
        completed_goals=completed_goals,
        achievements_status=achievements_status,
        streak=streak)


@app.route("/users/<username>")
@login_required
def view_user(username):
    user = User.query.filter(func.lower(User.username) == username.lower()).first()
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("social"))
    if user.id == current_user.id:
        return redirect(url_for("profile"))

    is_friend = user in current_user.friends
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    privacy = settings.privacy if settings else "public"
    if privacy == "private":
        flash("This profile is private.", "error")
        return redirect(url_for("social"))
    if privacy == "friends" and not is_friend:
        flash("This profile is friends-only.", "error")
        return redirect(url_for("social"))

    total_workouts  = Exercise.query.filter_by(user_id=user.id).count()
    total_distance  = db.session.query(db.func.sum(Exercise.distance)) \
                        .filter_by(user_id=user.id).scalar() or 0
    completed_goals = sum(1 for g in Goal.query.filter_by(user_id=user.id).all()
                          if g.is_completed_now)
    achievements_status = status_for_user(user.id)

    return render_template("friend_profile.html", active_page="social",
        viewed_user=user, is_friend=is_friend,
        total_workouts=total_workouts,
        total_distance=round(total_distance, 1),
        completed_goals=completed_goals,
        achievements_status=achievements_status)


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
        new_username = request.form.get("username", "").strip()
        new_email    = request.form.get("email", "").strip().lower()
        if new_username and new_username.lower() != current_user.username.lower():
            taken = User.query.filter(
                func.lower(User.username) == new_username.lower(),
                User.id != current_user.id,
            ).first()
            if not taken:
                current_user.username = new_username
        if new_email and new_email != current_user.email:
            if not User.query.filter_by(email=new_email).first():
                current_user.email = new_email
        current_user.first_name = request.form.get("first_name", "").strip() or None
        current_user.last_name  = request.form.get("last_name",  "").strip() or None
        current_user.bio        = request.form.get("bio", "").strip() or None

        new_password = request.form.get("new_password", "")
        if new_password:
            if not current_user.check_password(request.form.get("current_password", "")):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("settings"))
            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
                return redirect(url_for("settings"))
            current_user.set_password(new_password)

        db.session.commit()
        flash("Settings saved!", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", active_page="settings", s=s)


@app.route("/api/stats/weekly")
@login_required
def api_weekly_stats():
    from datetime import timedelta
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    labels, data = [], []
    for i in range(7):
        d     = week_start + timedelta(days=i)
        total = db.session.query(db.func.sum(Exercise.duration)) \
                    .filter_by(user_id=current_user.id, date=d).scalar() or 0
        labels.append(d.strftime("%a"))
        data.append(int(total))
    return jsonify({"labels": labels, "data": data})


@app.route("/api/users/search")
@login_required
def search_users():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    users = User.query.filter(
        User.username.ilike(f"%{q}%"),
        User.id != current_user.id
    ).limit(10).all()
    return jsonify([{"id": u.id, "username": u.username} for u in users])


@app.route("/api/friends/add/<int:user_id>", methods=["POST"])
@login_required
def add_friend(user_id):
    user = db.session.get(User, user_id)
    if user and user not in current_user.friends:
        current_user.friends.append(user)
        db.session.commit()
    return jsonify({"status": "ok"})


def init_db() -> None:
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
