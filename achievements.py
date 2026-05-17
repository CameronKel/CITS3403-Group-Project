"""Achievement registry. Definitions live in code (not the DB) so adding new
ones doesn't need a migration — only the user_achievements link table is
persisted."""
from dataclasses import dataclass
from typing import Callable, List

from models import Exercise, Goal, UserAchievement, db


@dataclass(frozen=True)
class Achievement:
    key: str
    name: str
    description: str
    emoji: str
    progress: Callable[[int], tuple]   # user_id -> (current, target)


def _count_workouts(user_id):
    return Exercise.query.filter_by(user_id=user_id).count()


def _first_workout(user_id):
    return (min(_count_workouts(user_id), 1), 1)


def _ten_workouts(user_id):
    return (min(_count_workouts(user_id), 10), 10)


def _marathon_session(user_id):
    has = Exercise.query.filter(
        Exercise.user_id == user_id,
        Exercise.duration >= 60,
    ).count()
    return (min(has, 1), 1)


def _distance_demon(user_id):
    total = db.session.query(
        db.func.coalesce(db.func.sum(Exercise.distance), 0.0)
    ).filter(Exercise.user_id == user_id).scalar() or 0.0
    return (min(int(total), 50), 50)


def _iron_will(user_id):
    n = Exercise.query.filter_by(user_id=user_id, intensity="High").count()
    return (min(n, 5), 5)


def _variety_pack(user_id):
    distinct = db.session.query(Exercise.type).filter_by(user_id=user_id).distinct().count()
    return (min(distinct, 5), 5)


def _goal_getter(user_id):
    done = sum(1 for g in Goal.query.filter_by(user_id=user_id).all() if g.is_completed_now)
    return (min(done, 1), 1)


ACHIEVEMENTS: List[Achievement] = [
    Achievement("first_workout",   "First Steps",      "Log your first workout",            "👟", _first_workout),
    Achievement("ten_workouts",    "Getting Serious",  "Log 10 workouts total",             "💪", _ten_workouts),
    Achievement("marathon_session","Marathon Mindset", "Complete a 60+ minute workout",     "⏱️", _marathon_session),
    Achievement("distance_demon",  "Distance Demon",   "Cover 50km of total distance",      "🏃", _distance_demon),
    Achievement("iron_will",       "Iron Will",        "Log 5 high-intensity workouts",     "🔥", _iron_will),
    Achievement("variety_pack",    "Variety Pack",     "Try 5 different exercise types",    "🎨", _variety_pack),
    Achievement("goal_getter",     "Goal Getter",      "Complete a fitness goal",           "🎯", _goal_getter),
]

BY_KEY = {a.key: a for a in ACHIEVEMENTS}


def award_achievements(user_id) -> List[str]:
    """Check all achievements; award any newly earned ones. Returns their keys."""
    earned = {ua.achievement_key
              for ua in UserAchievement.query.filter_by(user_id=user_id).all()}
    newly_earned = []
    for a in ACHIEVEMENTS:
        if a.key in earned:
            continue
        current, target = a.progress(user_id)
        if current >= target:
            db.session.add(UserAchievement(user_id=user_id, achievement_key=a.key))
            newly_earned.append(a.key)
    if newly_earned:
        db.session.commit()
    return newly_earned


def status_for_user(user_id):
    """Return a list of (Achievement, earned_at_or_None, current, target) tuples."""
    earned_map = {ua.achievement_key: ua.earned_at
                  for ua in UserAchievement.query.filter_by(user_id=user_id).all()}
    out = []
    for a in ACHIEVEMENTS:
        current, target = a.progress(user_id)
        out.append((a, earned_map.get(a.key), current, target))
    return out
