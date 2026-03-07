"""
Admin API Routes
Handles AI quiz generation, drafting, and publishing.
Strictly restricted to users with role="admin".
"""

from flask import Blueprint, jsonify, request, session
from app.extensions import db
from app.models.ai_quiz import AIQuiz, AIQuestion
from app.utils.helpers import require_admin
import uuid

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/admin/api")

@admin_api_bp.route("/save-quiz", methods=["POST"])
@require_admin
def save_quiz():
    """Save generated quiz as draft"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Create AIQuiz record
        new_quiz = AIQuiz(
            quiz_id=data.get("quiz_id") or str(uuid.uuid4())[:8],
            title=data.get("title", "Untitled Quiz"),
            topic=data.get("topic", "General"),
            difficulty=data.get("difficulty", "Medium"),
            status="draft",
            created_by=session.get("user_id")
        )
        db.session.add(new_quiz)
        db.session.flush() # Get ID

        # Add questions
        for idx, q_data in enumerate(data.get("questions", [])):
            options = q_data.get("options", ["", "", "", ""])
            new_q = AIQuestion(
                ai_quiz_id=new_quiz.id,
                question_text=q_data.get("question", ""),
                option_a=options[0] if len(options) > 0 else "",
                option_b=options[1] if len(options) > 1 else "",
                option_c=options[2] if len(options) > 2 else "",
                option_d=options[3] if len(options) > 3 else "",
                correct_answer=q_data.get("correct_answer", "A"),
                explanation=q_data.get("explanation", ""),
                order_index=idx
            )
            db.session.add(new_q)

        db.session.commit()
        return jsonify({
            "success": True, 
            "message": "Quiz saved as draft", 
            "quiz_id": new_quiz.quiz_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/publish-quiz", methods=["POST"])
@require_admin
def publish_quiz():
    """Move draft to published (sync with main Quiz model)"""
    data = request.get_json()
    quiz_id = data.get("quiz_id")
    
    ai_quiz = AIQuiz.query.filter_by(quiz_id=quiz_id).first()
    if not ai_quiz:
        return jsonify({"error": "Quiz not found"}), 404

    try:
        from app.models.quiz import Quiz
        from app.models.question import Question

        # 1. Create entry in main Quiz table
        published_quiz = Quiz(
            title=ai_quiz.title,
            is_published=True,
            is_active=False,
            is_locked=True # AI generated quizzes are usually locked for immediate play
        )
        db.session.add(published_quiz)
        db.session.flush()

        # 2. Sync questions
        for ai_q in ai_quiz.questions:
            main_q = Question(
                quiz_id=published_quiz.id,
                order=ai_q.order_index + 1,
                question=ai_q.question_text,
                option1=ai_q.option_a,
                option2=ai_q.option_b,
                option3=ai_q.option_c,
                option4=ai_q.option_d,
                answer=getattr(ai_q, f"option_{ai_q.correct_answer.lower()}"),
                explanation=ai_q.explanation,
                time_limit=30, # Default
                points=1
            )
            db.session.add(main_q)

        # 3. Mark AIQuiz as published
        ai_quiz.status = "published"
        
        db.session.commit()
        return jsonify({"success": True, "message": "Quiz published successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_api_bp.route("/quizzes/drafts", methods=["GET"])
@require_admin
def get_drafts():
    """List all draft quizzes"""
    drafts = AIQuiz.query.filter_by(status="draft").all()
    return jsonify([q.to_dict() for q in drafts])
