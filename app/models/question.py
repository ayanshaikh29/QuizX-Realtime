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
    question_type = db.Column(db.String(20), default="mcq") # mcq, checkbox, short_answer, true_false
    
    # Options are nullable to support Short Answer questions
    option1 = db.Column(db.String(200), nullable=True)
    option2 = db.Column(db.String(200), nullable=True)
    option3 = db.Column(db.String(200), nullable=True)
    option4 = db.Column(db.String(200), nullable=True)
    
    answer = db.Column(db.String(200), nullable=True) # Used for mcq, short_answer, true_false
    correct_answers = db.Column(db.Text, nullable=True) # Used for checkbox (comma-separated or JSON)
    explanation = db.Column(db.Text, nullable=True) # Detailed AI explanation
    time_limit = db.Column(db.Integer, default=30)
    points = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<Question {self.id}>'