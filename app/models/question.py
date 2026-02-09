"""
Question Model
"""
from app.extensions import db


class Question(db.Model):
    """Question model"""
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    question = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    time_limit = db.Column(db.Integer, default=30)
    
    def __repr__(self):
        return f'<Question {self.id}>'