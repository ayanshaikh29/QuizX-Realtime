"""
Chatbot Routes — POST /api/chat
"""

from flask import Blueprint, jsonify, request

from app.services import AIService

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    """
    Accepts JSON:
        { "message": "...", "mode": "...", "metadata": {} }

    Returns JSON:
        { "message": "...", "response": { ...AIService payload... } }
    """
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    mode = data.get("mode")
    metadata = data.get("metadata") or {}

    if not message:
        return jsonify({"error": "Field 'message' is required."}), 400

    ai_response = AIService.chat(message=message, mode=mode, metadata=metadata)

    return jsonify({"message": message, "response": ai_response})