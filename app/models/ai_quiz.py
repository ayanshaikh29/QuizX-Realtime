from datetime import datetime
from app.extensions import db

class AIQuiz(db.Model):
    __tablename__ = "ai_quiz"
    id            = db.Column(db.Integer, primary_key=True)
    quiz_id       = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title         = db.Column(db.String(255), nullable=False)
    topic         = db.Column(db.String(255), nullable=False)
    difficulty    = db.Column(db.String(50), nullable=False, default="Medium")
    status        = db.Column(db.String(20), nullable=False, default="draft")  # draft | published
    created_by    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    published_at  = db.Column(db.DateTime, nullable=True)

    questions = db.relationship("AIQuestion", backref="quiz", lazy=True, 
                                cascade="all, delete-orphan", order_by="AIQuestion.order_index")

    def to_dict(self):
        return {
            "quiz_id": self.quiz_id,
            "title": self.title,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "status": self.status,
            "questions": [q.to_dict() for q in self.questions]
        }

class AIQuestion(db.Model):
    __tablename__ = "ai_question"
    id             = db.Column(db.Integer, primary_key=True)
    ai_quiz_id     = db.Column(db.Integer, db.ForeignKey("ai_quiz.id"), nullable=False)
    question_text  = db.Column(db.Text, nullable=False)
    option_a       = db.Column(db.String(512), nullable=False)
    option_b       = db.Column(db.String(512), nullable=False)
    option_c       = db.Column(db.String(512), nullable=False)
    option_d       = db.Column(db.String(512), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False) # A, B, C, or D
    explanation    = db.Column(db.Text, nullable=True) # Added for Gemini-style details
    order_index    = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "order": self.order_index + 1,
            "question": self.question_text,
            "options": [self.option_a, self.option_b, self.option_c, self.option_d],
            "correct_answer": self.correct_answer,
            "explanation": self.explanation
        }