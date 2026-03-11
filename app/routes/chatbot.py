"""
Chatbot Routes — POST /api/chat, POST /generate-mcq, POST /create-quiz-from-ai
"""

from flask import Blueprint, jsonify, request, session, render_template

from app.services import AIService
from app.extensions import db
from app.models.quiz import Quiz

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chat-page")
def chat_page():
    """Full-page ChatGPT-style chat interface"""
    return render_template("chat.html")


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    is_admin = session.get("role") == "admin"

    if not message:
        return jsonify({"error": "Field 'message' is required."}), 400

    # If admin asks to "create", "generate" or "make" a quiz, use specialized engine
    keywords = ["create", "generate", "make", "quiz", "test", "assessment"]
    is_generation_request = any(k in message.lower() for k in keywords)

    if is_admin and is_generation_request:
        difficulty = data.get("difficulty", "medium")
        question_type = data.get("question_type", "mcq")
        ai_response = AIService.generate_quiz(
            prompt=message, difficulty=difficulty, question_type=question_type
        )
        # Wrap for chatbot UI consistency
        if ai_response.get("success"):
            quiz_data = ai_response.get("data")
            return jsonify({
                "message": message,
                "response": {
                    "reply": quiz_data.get("summary") or "Quiz generated successfully! Opening the builder...",
                    "quiz_data": quiz_data,
                    "type": "admin_quiz"
                }
            })
        else:
            return jsonify({
                "message": message,
                "response": {
                    "reply": "I encountered an error while generating your quiz. Please try a different prompt.",
                    "type": "error"
                }
            })

    ai_response = AIService.chat(message=message)
    return jsonify({"message": message, "response": ai_response})


# ------------------------------------------------------------------
# Dedicated MCQ generation endpoint for chatbot → quiz form flow
# ------------------------------------------------------------------

@chatbot_bp.route("/generate-mcq", methods=["POST"])
def generate_mcq():
    """Generate 10 MCQs from a topic prompt (admin only)."""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Admin access required."}), 403

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    difficulty = (data.get("difficulty") or "medium").strip()
    question_type = (data.get("question_type") or "mcq").strip()

    if not prompt:
        return jsonify({"success": False, "error": "Prompt is required."}), 400

    result = AIService.generate_quiz(
        prompt=prompt, difficulty=difficulty, question_type=question_type
    )
    return jsonify(result)


# ------------------------------------------------------------------
# Create a new quiz from AI-generated questions (admin only)
# ------------------------------------------------------------------

@chatbot_bp.route("/create-quiz-from-ai", methods=["POST"])
def create_quiz_from_ai():
    """Create a new Quiz row so the admin can redirect to its add-question page."""
    if session.get("role") != "admin":
        return jsonify({"success": False, "error": "Admin access required."}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or "AI Generated Quiz"

    try:
        quiz = Quiz(title=title, has_timer=True)
        db.session.add(quiz)
        db.session.commit()
        return jsonify({"success": True, "quiz_id": quiz.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500