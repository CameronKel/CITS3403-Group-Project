from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

friendships = db.Table(
    "friendships",
    db.Column("user_id",   db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("friend_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email           = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(256), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    first_name = db.Column(db.String(64), nullable=True)
    last_name  = db.Column(db.String(64), nullable=True)

    friends = db.relationship(
        "User",
        secondary=friendships,
        primaryjoin=lambda: User.id == friendships.c.user_id,
        secondaryjoin=lambda: User.id == friendships.c.friend_id,
        backref="friend_of",
        )
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"

class Exercise(db.Model):
    __tablename__ = "exercises"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type        = db.Column(db.String(64), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    duration    = db.Column(db.Integer, nullable=False)        
    intensity   = db.Column(db.String(16), nullable=False)    
    distance    = db.Column(db.Float, nullable=True)           
    notes       = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="exercises")

    def __repr__(self):
        return f"<Exercise {self.type} {self.date}>"


class Goal(db.Model):
    __tablename__ = "goals"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    goal_type     = db.Column(db.String(64), nullable=False)   
    target_value  = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, default=0.0, nullable=False)
    deadline      = db.Column(db.Date, nullable=False)
    completed     = db.Column(db.Boolean, default=False, nullable=False)
    completed_at  = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="goals")

    def __repr__(self):
        return f"<Goal {self.goal_type} target={self.target_value}>"
    

class FeedPost(db.Model):
    __tablename__ = "feed_posts"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_type   = db.Column(db.String(32), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=True)
    goal_id     = db.Column(db.Integer, db.ForeignKey("goals.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user     = db.relationship("User", backref="posts")
    exercise = db.relationship("Exercise", backref="feed_posts")
    goal     = db.relationship("Goal",     backref="feed_posts")

    def __repr__(self):
        return f"<FeedPost {self.post_type} by user {self.user_id}>"


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    workout_reminders = db.Column(db.Boolean, default=True,  nullable=False)
    goal_alerts       = db.Column(db.Boolean, default=True,  nullable=False)
    friend_activity   = db.Column(db.Boolean, default=False, nullable=False)
    streak_warnings   = db.Column(db.Boolean, default=True,  nullable=False)
    weekly_summary    = db.Column(db.Boolean, default=True,  nullable=False)
    training_days     = db.Column(db.String(32), default="Mon,Wed,Thu,Sat", nullable=False)
    reminder_time     = db.Column(db.String(8),  default="07:30",           nullable=False)
    privacy           = db.Column(db.String(16), default="public",          nullable=False)

    user = db.relationship("User", backref=db.backref("settings", uselist=False))

    def __repr__(self):
        return f"<UserSettings user={self.user_id}>"