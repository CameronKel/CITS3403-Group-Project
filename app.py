from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/log")
def log_exercise():
    return render_template("log_exercise.html", active_page="log_exercise")


@app.route("/history")
def history():
    return render_template("history.html", active_page="history")


@app.route("/history/<int:id>/edit")
def edit_exercise(id):
    return render_template("edit_exercise.html", active_page="history", exercise_id=id)


@app.route("/goals")
def goals():
    return render_template("goals.html", active_page="goals")


@app.route("/social")
def social():
    return render_template("social.html", active_page="social")


@app.route("/profile")
def profile():
    return render_template("profile.html", active_page="profile")


@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings")


if __name__ == "__main__":
    app.run(debug=True)
