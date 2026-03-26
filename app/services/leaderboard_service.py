"""
Leaderboard Service
Handles leaderboard generation and queries
"""
from app.extensions import db
from app.models import PartialAnswer, Question
from sqlalchemy import func


class LeaderboardService:
    """Leaderboard generation and management"""
    
    @staticmethod
    def build_leaderboard_payload(quiz_id, current_question_id=None):
        """
        Build full leaderboard payload for a quiz
        
        Returns:
            list: List of dicts with student, points, correct, incorrect, time, total
        """
        total_questions = Question.query.filter_by(quiz_id=quiz_id).count()
        
        rows = db.session.query(
            PartialAnswer.student,
            func.sum(PartialAnswer.points).label("total_points"),
            func.sum(
                db.case((PartialAnswer.is_correct == True, 1), else_=0)
            ).label("correct_count"),
            func.sum(
                db.case((PartialAnswer.is_correct == False, 1), else_=0)
            ).label("incorrect_count"),
            func.sum(PartialAnswer.time_taken).label("total_time"),
            func.max(PartialAnswer.submitted_at).label("latest_submission")
        ).filter_by(quiz_id=quiz_id).group_by(PartialAnswer.student).order_by(
            func.sum(PartialAnswer.points).desc(),
            func.max(PartialAnswer.submitted_at).asc()
        ).all()

        # Get fastest answer for the current question if provided
        fastest_student = None
        if current_question_id:
            fastest_ans = PartialAnswer.query.filter_by(
                quiz_id=quiz_id,
                question_id=current_question_id,
                is_correct=True
            ).order_by(PartialAnswer.time_taken.asc()).first()
            if fastest_ans:
                fastest_student = fastest_ans.student
        
        return [
            {
                "rank": idx + 1,
                "student": row.student,
                "points": int(row.total_points or 0),
                "correct": int(row.correct_count or 0),
                "incorrect": int(row.incorrect_count or 0),
                "time": int(row.total_time or 0),
                "total": total_questions,
                "latest_submission": row.latest_submission.isoformat() if row.latest_submission else None,
                "is_fastest": row.student == fastest_student
            }
            for idx, row in enumerate(rows)
        ]
    
    @staticmethod
    def get_leaderboard_data(quiz_id):
        """Get simple leaderboard data (name, score)"""
        points_query = db.session.query(
            PartialAnswer.student.label('name'),
            func.sum(PartialAnswer.points).label('score'),
            func.max(PartialAnswer.submitted_at).label('latest')
        ).filter_by(quiz_id=quiz_id)\
         .group_by(PartialAnswer.student)\
         .order_by(
             func.sum(PartialAnswer.points).desc(),
             func.max(PartialAnswer.submitted_at).asc()
         ).all()
        
        return [{"name": r.name, "score": int(r.score)} for r in points_query]
    
    @staticmethod
    def get_question_leaderboard(quiz_id, question_id):
        """Get leaderboard for a specific question"""
        from app.models import Quiz
        
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return []
        
        if quiz.has_timer:
            answers = PartialAnswer.query.filter_by(
                quiz_id=quiz_id,
                question_id=question_id,
                is_correct=True
            ).order_by(
                PartialAnswer.time_taken.asc(),
                PartialAnswer.submitted_at.asc()
            ).limit(10).all()
        else:
            answers = PartialAnswer.query.filter_by(
                quiz_id=quiz_id,
                question_id=question_id,
                is_correct=True
            ).order_by(
                PartialAnswer.submitted_at.asc()
            ).limit(10).all()
        
        return [
            {
                "rank": i + 1,
                "student": a.student,
                "time_taken": a.time_taken,
                "points": a.points
            }
            for i, a in enumerate(answers)
        ]