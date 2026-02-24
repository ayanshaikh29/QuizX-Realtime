"""
Point Service
Handles all scoring and ranking logic based on flat points
"""
from app.extensions import db
from app.models import PartialAnswer, Quiz, Question
from app.utils import now_utc

class PointService:
    """Server-authoritative point scoring system replacing XP"""
    
    @staticmethod
    def calculate_points(is_correct, question_id):
        """
        Calculate flat points based purely on correctness and the question's point value.
        No time or rank bonuses.
        
        Args:
            is_correct (bool): Whether the answer is correct
            question_id (int): ID of the question to fetch point value
        
        Returns:
            int: Total points earned
        """
        if not is_correct:
            return 0
            
        question = Question.query.get(question_id)
        if not question:
            return 1 # Fallback to 1 point if question doesn't exist
            
        return question.points
    
    @staticmethod
    def update_question_rank_bonuses(quiz_id, question_id):
        """
        No-op method kept for backwards compatibility in routes.
        Rank bonuses are no longer calculated in the Point System.
        """
        pass
