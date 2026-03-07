"""
Chatbot Routes — POST /api/chat
"""

from flask import Blueprint, jsonify, request, session, render_template

from app.services import AIService

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
        ai_response = AIService.generate_quiz(prompt=message)
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