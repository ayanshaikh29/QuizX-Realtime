"""
Admin Routes
All admin functionality: dashboard, quizzes, questions, live control, analytics
ENHANCED: Added quiz data clearing on start to prevent old leaderboard data
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import db, socketio, quiz_state
from app.models import User, Quiz, Question, PartialAnswer, Result
from app.utils import require_admin, now_utc, utc_to_ist, generate_join_code
from app.services import ScoringService, LeaderboardService
from sqlalchemy import func
import time

admin_bp = Blueprint('admin', __name__)


def clear_quiz_session_data(quiz_id):
    """
    Clear all partial answers for a quiz session
    This prevents old data from appearing in new quiz sessions
    
    Args:
        quiz_id: The quiz ID to clear
        
    Returns:
        Dict with counts of deleted records
    """
    print(f"\n{'='*60}")
    print(f"CLEARING SESSION DATA FOR QUIZ {quiz_id}")
    print(f"{'='*60}")
    
    # Delete all partial answers for this quiz
    partial_count = PartialAnswer.query.filter_by(quiz_id=quiz_id).count()
    PartialAnswer.query.filter_by(quiz_id=quiz_id).delete()
    
    # Commit the deletion
    db.session.commit()
    
    print(f"✓ Deleted {partial_count} partial answers")
    print(f"{'='*60}\n")
    
    return {
        'partial_answers_cleared': partial_count,
        'quiz_id': quiz_id,
    }


@admin_bp.route('/dashboard')
@require_admin
def dashboard():
    """Admin dashboard"""
    total_quizzes = Quiz.query.count()
    active_quizzes = Quiz.query.filter_by(is_active=True).count()
    total_students = User.query.filter_by(role='student').count()
    total_responses = Result.query.count()
    recent_results = Result.query.order_by(Result.submitted_at.desc()).limit(5).all()
    
    return render_template(
        'admin_dashboard.html',
        total_quizzes=total_quizzes,
        active_quizzes=active_quizzes,
        total_students=total_students,
        total_responses=total_responses,
        recent_results=recent_results
    )


@admin_bp.route('/quizzes', methods=['GET', 'POST'])
@require_admin
def quizzes():
    """Quiz management"""
    if request.method == 'POST':
        title = request.form.get('title')
        quiz_type = request.form.get('quiz_type')
        
        if not title:
            flash('Quiz title is required', 'error')
            return redirect(url_for('admin.quizzes'))
        
        has_timer = (quiz_type == 'timer')
        quiz = Quiz(title=title, has_timer=has_timer)
        db.session.add(quiz)
        db.session.commit()
        
        flash(
            f"{'Timer-based' if has_timer else 'Normal'} quiz created successfully! Now add questions.",
            'success',
        )
        return redirect(url_for('admin.add_question', quiz_id=quiz.id))
    
    all_quizzes = Quiz.query.all()
    return render_template('admin_quiz.html', quizzes=all_quizzes)


@admin_bp.route('/add-question/<int:quiz_id>', methods=['GET', 'POST'])
@require_admin
def add_question(quiz_id):
    """Add questions to quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.is_active:
        flash('Cannot add questions to an active quiz.', 'error')
        return redirect(url_for('admin.quizzes'))
    
    if request.method == 'POST':
        # 1. Update Quiz Configuration
        show_leaderboard_str = request.form.get('show_leaderboard_each_question', 'false')
        quiz.show_leaderboard_each_question = (show_leaderboard_str.lower() == 'true')
        
        if quiz.has_timer:
            quiz.timer_mode = request.form.get('timer_mode', 'per_question')
            if quiz.timer_mode == 'overall':
                try:
                    quiz.total_quiz_time = int(request.form.get('total_quiz_time', 15))
                except ValueError:
                    quiz.total_quiz_time = 15
            else:
                quiz.total_quiz_time = None
        
        # 2. Process Questions
        questions_data = request.form.getlist('question[]')
        added = False
        
        for i, qtext in enumerate(questions_data):
            if not qtext.strip():
                continue
            
            ans_index = request.form.get(f'answer_{i}')
            if not ans_index:
                continue
            
            option_key = f'option{ans_index}_{i}'
            correct_answer = request.form.get(option_key)
            if not correct_answer:
                continue
            
            if quiz.has_timer:
                time_str = request.form.get(f'time_{i}', '30')
                try:
                    time_limit = max(5, int(time_str))
                except ValueError:
                    time_limit = 30
            else:
                time_limit = 0
            
            points_str = request.form.get(f'points_{i}', '1')
            try:
                points = int(points_str)
            except ValueError:
                points = 1
            
            q = Question(
                quiz_id=quiz_id,
                order=i + 1,
                question=qtext,
                option1=request.form.get(f'option1_{i}', ''),
                option2=request.form.get(f'option2_{i}', ''),
                option3=request.form.get(f'option3_{i}', ''),
                option4=request.form.get(f'option4_{i}', ''),
                answer=correct_answer,
                time_limit=time_limit,
                points=points,
            )
            db.session.add(q)
            added = True
        
        if added:
            db.session.commit()
            flash('Questions added successfully!', 'success')
        else:
            flash('No valid questions were added.', 'warning')
        
        return redirect(url_for('admin.add_question', quiz_id=quiz_id))
    
    template_name = 'add_question.html' if quiz.has_timer else 'normal_add_question.html'
    return render_template(template_name, quiz=quiz)


@admin_bp.route('/end-questions/<int:quiz_id>')
@require_admin
def end_questions(quiz_id):
    """Lock quiz questions"""
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_locked = True
    db.session.commit()
    flash('Question adding locked.', 'info')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/publish-quiz/<int:quiz_id>')
@require_admin
def publish_quiz(quiz_id):
    """Publish quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not quiz.is_locked:
        flash('Lock questions first before publishing!', 'error')
        return redirect(url_for('admin.quizzes'))
    
    quiz.is_published = True
    quiz.is_active = False
    quiz.start_time = now_utc()
    quiz.published_at = now_utc()
    quiz.publish_count = (quiz.publish_count or 0) + 1
    quiz.paused_seconds = 0
    quiz.is_paused = False
    
    if not quiz.join_code:
        quiz.join_code = generate_join_code()
    
    quiz_state[quiz.id] = {'current_qindex': 0}
    db.session.commit()
    
    ist_time = utc_to_ist(quiz.published_at)
    flash(
        f"Quiz published at {ist_time.strftime('%d %b %Y, %I:%M %p')} IST "
        f"(Published {quiz.publish_count} times)",
        'success',
    )
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/pause-quiz/<int:quiz_id>')
@require_admin
def pause_quiz(quiz_id):
    """Pause quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and not quiz.is_paused:
        quiz.is_paused = True
        quiz.paused_at = now_utc()
        db.session.commit()
        flash('Quiz paused.', 'info')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/resume-quiz/<int:quiz_id>')
@require_admin
def resume_quiz(quiz_id):
    """Resume paused quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and quiz.is_paused:
        paused_time = (now_utc() - quiz.paused_at).total_seconds()
        quiz.paused_seconds += int(paused_time)
        quiz.is_paused = False
        quiz.paused_at = None
        db.session.commit()
        flash('Quiz resumed.', 'info')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/stop-quiz/<int:quiz_id>')
@require_admin
def stop_quiz(quiz_id):
    """Stop quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_active = False
    quiz.is_published = False
    quiz.is_paused = False
    quiz.paused_at = None
    quiz.paused_seconds = 0
    db.session.commit()
    
    quiz_state.pop(quiz_id, None)
    
    socketio.emit(
        'quiz_stopped',
        {'quiz_id': quiz_id},
        room=f"quiz_{quiz_id}"
    )
    
    flash('Quiz stopped successfully.', 'info')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/start-quiz/<int:quiz_id>')
@require_admin
def start_quiz(quiz_id):
    """
    Start quiz
    CRITICAL: Clears old partial answers to prevent old leaderboard data
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if quiz.is_active:
        flash('Quiz is already active!', 'warning')
        return redirect(url_for('admin.live_control', quiz_id=quiz_id))
    
    # ═══════════════════════════════════════════════════════════
    # CRITICAL FIX: Clear old partial answers before starting
    # This prevents old data from appearing in the leaderboard
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"STARTING QUIZ: {quiz.title} (ID: {quiz_id})")
    print(f"{'='*60}")
    
    # Clear previous session data
    cleared = clear_quiz_session_data(quiz_id)
    print(f"✓ Cleared {cleared['partial_answers_cleared']} old answers")
    print(f"✓ Quiz data is now fresh and ready")
    print(f"{'='*60}\n")
    
    # Now start the quiz
    quiz.is_active = True
    quiz.is_paused = False
    
    # Initialize quiz state
    if quiz.has_timer:
        quiz_state[quiz_id] = {
            'current_qindex': 0,
            'started_at': time.time()
        }
    
    db.session.commit()
    
    # Notify all students in waiting room
    socketio.emit('begin_quiz', {
        'quiz_id': quiz_id,
        'message': 'Quiz is starting now!'
    }, room=f'waiting_room_{quiz_id}')
    
    # Tell students to join the quiz room
    socketio.emit('join_quiz_room', {
        'quiz_id': quiz_id
    }, room=f'waiting_room_{quiz_id}')
    
    flash(f'Quiz "{quiz.title}" is now LIVE! 🚀 Old data cleared.', 'success')
    return redirect(url_for('admin.live_control', quiz_id=quiz_id))


@admin_bp.route('/reset-quiz/<int:quiz_id>', methods=['POST'])
@require_admin
def reset_quiz(quiz_id):
    """
    Reset quiz completely
    Clears all data and resets to initial state
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    print(f"\n{'='*60}")
    print(f"RESETTING QUIZ: {quiz.title} (ID: {quiz_id})")
    print(f"{'='*60}")
    
    # Clear all session data
    cleared = clear_quiz_session_data(quiz_id)
    
    # Reset quiz state
    quiz.is_active = False
    quiz.is_paused = False
    quiz.current_question_index = 0
    quiz.paused_at = None
    quiz.paused_seconds = 0
    
    # Clear quiz_state if exists
    if quiz_id in quiz_state:
        del quiz_state[quiz_id]
    
    db.session.commit()
    
    print(f"✓ Quiz reset complete")
    print(f"✓ Cleared {cleared['partial_answers_cleared']} answers")
    print(f"{'='*60}\n")
    
    flash(
        f'Quiz "{quiz.title}" has been reset. '
        f'All progress cleared ({cleared["partial_answers_cleared"]} answers deleted).',
        'info'
    )
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/live-control/<int:quiz_id>')
@require_admin
def live_control(quiz_id):
    """Live quiz control"""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    
    current_index = quiz_state.get(quiz_id, {}).get('current_qindex', 0)
    current_question = questions[current_index] if current_index < len(questions) else None
    
    return render_template(
        'admin_live_control.html',
        quiz=quiz,
        questions=questions,
        total_questions=len(questions),
        current_index=current_index,
        current_question=current_question
    )


@admin_bp.route('/live-leaderboard/<int:quiz_id>')
@require_admin
def live_leaderboard(quiz_id):
    """Admin live leaderboard view"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get all questions for the quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    total_questions = len(questions)
    
    # Get current question index from quiz state
    current_index = quiz_state.get(quiz_id, {}).get('current_qindex', 0)
    
    # Get current question
    current_question = None
    if questions and 0 <= current_index < len(questions):
        current_question = questions[current_index]
    
    # Determine if this is the last question
    is_last = (current_index + 1 >= total_questions) if total_questions > 0 else True
    
    # Get qindex from query params (for compatibility)
    qindex = request.args.get('qindex', current_index, type=str)
    
    print(f"\n{'='*60}")
    print(f"ADMIN LIVE LEADERBOARD")
    print(f"{'='*60}")
    print(f"Quiz ID: {quiz_id}")
    print(f"Quiz Title: {quiz.title}")
    print(f"Total Questions: {total_questions}")
    print(f"Current Index: {current_index}")
    print(f"Is Last: {is_last}")
    print(f"Query param qindex: {qindex}")
    print(f"{'='*60}\n")
    
    return render_template(
        'admin_live_leaderboard.html',
        quiz=quiz,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        qindex=qindex,
        current_index=current_index,
        total_questions=total_questions,
        is_last=is_last,
        current_question=current_question,
    )


@admin_bp.route('/analytics/<int:quiz_id>')
@require_admin
def analytics(quiz_id):
    """Quiz analytics"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    total_participants = db.session.query(
        PartialAnswer.student
    ).filter_by(quiz_id=quiz_id).distinct().count()
    
    total_answers = PartialAnswer.query.filter_by(quiz_id=quiz_id).count()
    correct_answers = PartialAnswer.query.filter_by(
        quiz_id=quiz_id, is_correct=True
    ).count()
    
    accuracy_rate = int((correct_answers / total_answers) * 100) if total_answers else 0
    
    avg_time = int(
        db.session.query(func.avg(PartialAnswer.time_taken))
        .filter_by(quiz_id=quiz_id).scalar() or 0
    )
    
    completion_rate = 100
    
    question_data = []
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for q in questions:
        total_q = PartialAnswer.query.filter_by(
            quiz_id=quiz_id, question_id=q.id
        ).count()
        correct_q = PartialAnswer.query.filter_by(
            quiz_id=quiz_id, question_id=q.id, is_correct=True
        ).count()
        avg_q_time = db.session.query(func.avg(PartialAnswer.time_taken))\
            .filter_by(quiz_id=quiz_id, question_id=q.id).scalar() or 0
        
        correct_pct = int((correct_q / total_q) * 100) if total_q else 0
        difficulty = 'easy' if correct_pct > 70 else 'medium' if correct_pct > 40 else 'hard'
        
        question_data.append({
            'text': q.question,
            'difficulty': difficulty,
            'correct_pct': correct_pct,
            'avg_time': int(avg_q_time),
        })
    
    top_students = db.session.query(
        PartialAnswer.student.label('name'),
        func.sum(PartialAnswer.points).label('score')
    ).filter_by(quiz_id=quiz_id)\
     .group_by(PartialAnswer.student)\
     .order_by(func.sum(PartialAnswer.points).desc())\
     .limit(5).all()
    
    stats = {
        "total_attempts": total_participants,
        "avg_score": accuracy_rate,
        "avg_time": avg_time,
        "pass_rate": completion_rate
    }

# Fix performer format for template
    top_performers = [
        {
            "username": student.name,
            "score": student.score
        }
        for student in top_students
    ]

# Fix question data format for template
    questions_data = [
        {
            "text": q["text"],
            "success_rate": q["correct_pct"],
            "avg_time": q["avg_time"],
            "difficulty": q["difficulty"].capitalize()
        }
        for q in question_data
    ]

    return render_template(
        'admin_analytics.html',
        quiz=quiz,
        stats=stats,
        top_performers=top_performers,
        questions_data=questions_data
    )

from flask import Blueprint, render_template

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/analytics')
def analytics():
    return render_template(
        'admin_analytics.html',
        quiz={"title": "Sample Quiz"},
        total_participants=120,
        accuracy_rate=78,
        avg_time=14,
        completion_rate=92,
        question_data=[],
        top_students=[]
    )

@admin_bp.route('/delete-quiz/<int:quiz_id>')
@require_admin
def delete_quiz(quiz_id):
    """Delete quiz and all associated data"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Delete all associated data
    Question.query.filter_by(quiz_id=quiz_id).delete()
    PartialAnswer.query.filter_by(quiz_id=quiz_id).delete()
    Result.query.filter_by(quiz_id=quiz_id).delete()
    
    # Delete the quiz
    db.session.delete(quiz)
    db.session.commit()
    
    # Clean up quiz_state
    quiz_state.pop(quiz_id, None)
    
    flash('Quiz and all associated data deleted successfully.', 'info')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/rename-quiz', methods=['POST'])
@require_admin
def rename_quiz():
    """Rename quiz"""
    quiz_id = request.form.get('quiz_id')
    new_title = request.form.get('new_title')
    quiz = Quiz.query.get(quiz_id)
    
    if quiz and new_title:
        quiz.title = new_title
        db.session.commit()
        flash('Quiz renamed successfully!', 'success')
    
    return redirect(url_for('admin.quizzes'))


# ═══════════════════════════════════════════════════════════
# SOCKET.IO EVENT HANDLERS
# ═══════════════════════════════════════════════════════════

@socketio.on('admin_start_quiz')
def handle_admin_start_quiz(data):
    """
    Admin starts quiz via Socket.IO
    Clears old data before starting
    """
    quiz_id = data.get('quiz_id')
    
    if not quiz_id:
        return {'error': 'No quiz_id provided'}
    
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        return {'error': 'Quiz not found'}
    
    # Clear old data
    print(f"Admin starting quiz {quiz_id} via Socket.IO - clearing old data")
    cleared = clear_quiz_session_data(quiz_id)
    
    # Start quiz
    quiz.is_active = True
    quiz.is_paused = False
    
    if quiz.has_timer:
        quiz_state[quiz_id] = {
            'current_qindex': 0,
            'started_at': time.time()
        }
    
    db.session.commit()
    
    # Notify all participants
    socketio.emit(
        'quiz_started',
        {
            'quiz_id': quiz_id,
            'title': quiz.title,
            'has_timer': quiz.has_timer,
            'timestamp': time.time()
        },
        room=f"quiz_{quiz_id}"
    )
    
    return {
        'success': True,
        'cleared': cleared['partial_answers_cleared'],
        'quiz_id': quiz_id
    }


@socketio.on("admin_finish_quiz")
def handle_admin_finish_quiz(data):
    quiz_id = data.get("quiz_id")

    if not quiz_id:
        return {"error": "No quiz_id provided"}

    # Stop quiz in DB
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        quiz.is_active = False
        db.session.commit()

    # Emit to ALL students
    socketio.emit(
        "quiz_finished",
        {"quiz_id": quiz_id},
        room=f"quiz_{quiz_id}"  # ✅ FIXED
    )

    print(f"Quiz {quiz_id} finished by admin")

    return {"success": True}


@socketio.on('admin_reset_quiz')
def handle_admin_reset_quiz(data):
    """
    Admin resets quiz via Socket.IO - clears all data
    """
    quiz_id = data.get('quiz_id')
    
    if not quiz_id:
        return {'error': 'No quiz_id provided'}
    
    # Clear all data
    cleared = clear_quiz_session_data(quiz_id)
    
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        quiz.is_active = False
        quiz.is_paused = False
        quiz.current_question_index = 0
        db.session.commit()
    
    # Clear quiz_state
    quiz_state.pop(quiz_id, None)
    
    # Notify admin
    socketio.emit(
        'quiz_reset_complete',
        {
            'quiz_id': quiz_id,
            'cleared': cleared
        },
        room=f"admin_{quiz_id}"
    )
    
    return {
        'success': True,
        'cleared': cleared['partial_answers_cleared'],
        'quiz_id': quiz_id
    }


@socketio.on('admin_clear_quiz_data')
def handle_admin_clear_quiz_data(data):
    """
    Admin manually clears quiz data via Socket.IO
    Useful for debugging or manual cleanup
    """
    quiz_id = data.get('quiz_id')
    
    if not quiz_id:
        return {'error': 'No quiz_id provided'}
    
    cleared = clear_quiz_session_data(quiz_id)
    
    return {
        'success': True,
        'cleared': cleared['partial_answers_cleared'],
        'quiz_id': quiz_id,
        'message': f"Cleared {cleared['partial_answers_cleared']} partial answers"
    }