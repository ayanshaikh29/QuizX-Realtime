from flask import Blueprint, redirect, url_for, session, flash, send_from_directory, current_app
from app.models import Quiz
import os

public_bp = Blueprint('public', __name__)


@public_bp.route('/favicon.ico')
def favicon():
    """Serve favicon with long cache headers to prevent flash on navigation"""
    return send_from_directory(
        os.path.join(current_app.root_path, '..', 'static'),
        'favicon.png',
        mimetype='image/png',
        max_age=31536000  # 1 year cache
    )

@public_bp.route('/quiz/join/<code>')
def join_quiz_public(code):
    """
    Google Form style join link
    Uses EXISTING login (username + password)
    """

    quiz = Quiz.query.filter_by(
        join_code=code.upper(),
        is_published=True
    ).first()

    if not quiz:
        return "Quiz not found or inactive", 404

    # 🚫 Admin cannot attempt quiz
    if session.get('role') == 'admin':
        flash('Admins cannot attempt quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))

    # ❗ Not logged in → send to SAME login page
    if 'user_id' not in session:
        session['next_url'] = url_for(
            'student.waiting_room',
            quiz_id=quiz.id
        )
        return redirect(url_for('auth.login'))

    # ✅ Logged in student → direct join
    return redirect(url_for('student.waiting_room', quiz_id=quiz.id))
