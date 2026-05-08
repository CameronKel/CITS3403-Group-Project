from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email           = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(256), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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