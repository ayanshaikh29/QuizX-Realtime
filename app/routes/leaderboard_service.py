"""
Leaderboard Service
Handles leaderboard calculations and data aggregation
CRITICAL FIX: Only fetch and return data for the specified quiz_id
"""
from app.models import PartialAnswer, Result
from sqlalchemy import func


class LeaderboardService:
    """Service for leaderboard operations"""
    
    @staticmethod
    def build_leaderboard_payload(quiz_id):
        """
        Build leaderboard from PartialAnswer table for a specific quiz
        CRITICAL: Only include data for the specified quiz_id
        
        Returns:
            List of dicts with student, points, correct, time
        """
        print(f"\n=== BUILDING LEADERBOARD FOR QUIZ {quiz_id} ===")
        
        # CRITICAL FIX: Filter by quiz_id to get ONLY current quiz data
        partials = PartialAnswer.query.filter_by(quiz_id=quiz_id).all()
        
        print(f"Found {len(partials)} partial answers for quiz {quiz_id}")
        
        # Group by student
        student_data = {}
        for p in partials:
            student_name = p.student
            if student_name not in student_data:
                student_data[student_name] = {
                    'student': student_name,
                    'points': 0,
                    'correct': 0,
                    'time': 0,
                    'quiz_id': quiz_id  # Add quiz_id to each entry
                }
            
            student_data[student_name]['points'] += p.points
            student_data[student_name]['time'] += p.time_taken
            if p.is_correct:
                student_data[student_name]['correct'] += 1
        
        leaderboard = list(student_data.values())
        
        # Sort by points (desc), then correct (desc), then time (asc)
        leaderboard.sort(key=lambda x: (-x['points'], -x['correct'], x['time']))
        
        print(f"Leaderboard built with {len(leaderboard)} students:")
        for idx, entry in enumerate(leaderboard[:5]):  # Print top 5
            print(f"  {idx+1}. {entry['student']}: {entry['points']} pts, {entry['correct']} correct, {entry['time']}s")
        
        print(f"=== LEADERBOARD BUILD COMPLETE ===\n")
        
        return leaderboard
    
    @staticmethod
    def get_question_leaderboard(quiz_id, question_id):
        """
        Get leaderboard for a specific question
        CRITICAL: Only include data for the specified quiz_id and question_id
        
        Returns:
            List of dicts with student, points, time_taken, is_correct
        """
        print(f"\n=== BUILDING QUESTION LEADERBOARD ===")
        print(f"Quiz ID: {quiz_id}, Question ID: {question_id}")
        
        # CRITICAL FIX: Filter by both quiz_id AND question_id
        answers = (
            PartialAnswer.query
            .filter_by(quiz_id=quiz_id, question_id=question_id)
            .order_by(PartialAnswer.points.desc(), PartialAnswer.time_taken.asc())
            .all()
        )
        
        print(f"Found {len(answers)} answers for this question")
        
        leaderboard = []
        for ans in answers:
            leaderboard.append({
                'student': ans.student,
                'points': ans.points,
                'time_taken': ans.time_taken,
                'is_correct': ans.is_correct,
                'quiz_id': quiz_id,
                'question_id': question_id
            })
        
        print(f"Question leaderboard built with {len(leaderboard)} entries")
        print(f"=== QUESTION LEADERBOARD COMPLETE ===\n")
        
        return leaderboard
    
    @staticmethod
    def get_final_results(quiz_id):
        """
        Get final results from Result table for a specific quiz
        CRITICAL: Only include data for the specified quiz_id
        
        Returns:
            List of Result objects sorted by total_points
        """
        print(f"\n=== GETTING FINAL RESULTS FOR QUIZ {quiz_id} ===")
        
        # CRITICAL FIX: Filter by quiz_id
        results = (
            Result.query
            .filter_by(quiz_id=quiz_id)
            .order_by(Result.total_points.desc(), Result.time_taken.asc())
            .all()
        )
        
        print(f"Found {len(results)} final results for quiz {quiz_id}")
        
        return results
    
    @staticmethod
    def clear_quiz_data(quiz_id):
        """
        Clear all partial answers and results for a quiz
        Used when restarting a quiz to prevent old data from appearing
        
        Args:
            quiz_id: The quiz ID to clear data for
        """
        print(f"\n=== CLEARING DATA FOR QUIZ {quiz_id} ===")
        
        from app.extensions import db
        
        # Delete all partial answers for this quiz
        partial_count = PartialAnswer.query.filter_by(quiz_id=quiz_id).delete()
        print(f"Deleted {partial_count} partial answers")
        
        # Delete all results for this quiz
        result_count = Result.query.filter_by(quiz_id=quiz_id).delete()
        print(f"Deleted {result_count} results")
        
        db.session.commit()
        
        print(f"=== DATA CLEARED FOR QUIZ {quiz_id} ===\n")
        
        return {
            'partial_answers_deleted': partial_count,
            'results_deleted': result_count
        }
    
    @staticmethod
    def get_student_stats(quiz_id, student_name):
        """
        Get statistics for a specific student in a quiz
        
        Args:
            quiz_id: The quiz ID
            student_name: The student's name
            
        Returns:
            Dict with student stats
        """
        # Get partial answers for this student
        partials = PartialAnswer.query.filter_by(
            quiz_id=quiz_id,
            student=student_name
        ).all()
        
        if not partials:
            return {
                'student': student_name,
                'quiz_id': quiz_id,
                'points': 0,
                'correct': 0,
                'total_answered': 0,
                'time': 0
            }
        
        total_points = sum(p.points for p in partials)
        correct_count = sum(1 for p in partials if p.is_correct)
        total_time = sum(p.time_taken for p in partials)
        
        return {
            'student': student_name,
            'quiz_id': quiz_id,
            'points': total_points,
            'correct': correct_count,
            'total_answered': len(partials),
            'time': total_time
        }