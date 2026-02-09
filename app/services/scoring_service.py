"""
Scoring Service
Handles all scoring and ranking logic
"""
from app.extensions import db
from app.models import PartialAnswer, Quiz, Question
from app.utils import now_utc


class ScoringService:
    """Server-authoritative scoring system"""
    
    @staticmethod
    def calculate_points(is_correct, time_taken=None, time_limit=None, rank=None, has_timer=False):
        """
        Calculate points based on correctness, speed, and rank
        
        Args:
            is_correct: Whether the answer is correct
            time_taken: Time taken in seconds
            time_limit: Question time limit
            rank: User's rank for this question
            has_timer: Whether the quiz uses timers
        
        Returns:
            int: Total points earned
        """
        if not is_correct:
            return 0
        
        points = 100  # Base points
        
        # Speed bonus only if quiz has timer
        if has_timer and time_taken is not None and time_limit is not None:
            time_percentage = (time_taken / time_limit) * 100
            if time_percentage <= 25:
                speed_bonus = 50
            elif time_percentage <= 50:
                speed_bonus = 40
            elif time_percentage <= 75:
                speed_bonus = 30
            else:
                speed_bonus = 20
            points += speed_bonus
        
        # Rank bonus
        if rank == 1:
            points += 50
        elif rank == 2:
            points += 30
        elif rank == 3:
            points += 20
        elif rank in [4, 5]:
            points += 10
        
        return points
    
    @staticmethod
    def update_question_rank_bonuses(quiz_id, question_id):
        """
        Update rank bonuses for all correct answers to a question
        """
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return
        
        # Get all correct answers for this question, ordered by time or submission
        if quiz.has_timer:
            correct_answers = PartialAnswer.query.filter_by(
                quiz_id=quiz_id,
                question_id=question_id,
                is_correct=True,
            ).order_by(
                PartialAnswer.time_taken.asc(),
                PartialAnswer.submitted_at.asc(),
            ).all()
        else:
            correct_answers = PartialAnswer.query.filter_by(
                quiz_id=quiz_id,
                question_id=question_id,
                is_correct=True,
            ).order_by(
                PartialAnswer.submitted_at.asc(),
            ).all()
        
        # Get the question to access time_limit
        question = Question.query.get(question_id)
        if not question:
            return
        
        # Recalculate points with rank bonuses
        for idx, partial in enumerate(correct_answers):
            rank = idx + 1
            new_points = ScoringService.calculate_points(
                is_correct=True,
                time_taken=partial.time_taken,
                time_limit=question.time_limit if quiz.has_timer else None,
                rank=rank,
                has_timer=quiz.has_timer,
            )
            partial.points = new_points
        
        db.session.commit()