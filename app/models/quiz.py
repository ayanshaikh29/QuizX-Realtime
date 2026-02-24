"""
Quiz Model
"""
from app.extensions import db
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


class Quiz(db.Model):
    """Quiz model"""
    __tablename__ = 'quiz'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    has_timer = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    publish_count = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime)
    is_locked = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    join_code = db.Column(db.String(10), unique=True)
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    paused_seconds = db.Column(db.Integer, default=0)
    
    # Advanced Configuration
    show_leaderboard_each_question = db.Column(db.Boolean, default=True)
    timer_mode = db.Column(db.String(20), default='per_question') # 'per_question' or 'overall'
    total_quiz_time = db.Column(db.Integer, nullable=True) # in minutes
    
    def __repr__(self):
        return f'<Quiz {self.title}>'