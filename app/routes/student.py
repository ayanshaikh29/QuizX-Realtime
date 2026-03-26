"""
Student Routes
All student functionality: dashboard, quiz attempt, results, history
CRITICAL FIX: Prevent auto-redirect to admin dashboard
LEADERBOARD FIX: Only show current quiz data, filter out past quiz data
SEPARATION UPDATE: Leaderboard is now a separate page
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.extensions import db, socketio, quiz_state
from app.models import Quiz, Question, PartialAnswer, Result
from app.utils import require_student, ensure_guest_student, now_utc
from app.services import PointService, LeaderboardService
import time

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@require_student
def dashboard():
    """Student dashboard"""
    return render_template('student_dashboard.html', username=session.get('username'))

@student_bp.route('/quizzes')
def quizzes():
    """List available quizzes - NO LOGIN REQUIRED (allows guests)"""
    # DEBUG
    print(f"\n{'='*60}")
    print("STUDENT QUIZZES PAGE - DEBUG")
    print(f"{'='*60}")
    
    # CRITICAL: Block only admins, allow students AND guests
    if session.get('role') == 'admin':
        print("⚠️ Admin detected, redirecting to admin dashboard")
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Ensure guest session
    ensure_guest_student()
    
    # SHOW ALL PUBLISHED QUIZZES
    from app.models import Question, GroupStudent
    all_quizzes = Quiz.query.filter_by(is_published=True).order_by(Quiz.published_at.desc()).all()
    
    # GROUP FILTER: If a quiz has a group_id, only show it to students in that group
    user_id = session.get('user_id')
    if user_id and user_id != -1:
        # Logged-in student: get their group IDs
        my_group_ids = [gs.group_id for gs in GroupStudent.query.filter_by(student_id=user_id).all()]
        filtered = []
        for q in all_quizzes:
            if q.group_id is None:
                filtered.append(q)  # No group restriction
            elif q.group_id in my_group_ids:
                filtered.append(q)  # Student is in the group
        all_quizzes = filtered
    else:
        # Guest: only show quizzes with no group restriction
        all_quizzes = [q for q in all_quizzes if q.group_id is None]
    
    print(f"Found {len(all_quizzes)} published quizzes:")
    for q in all_quizzes:
        print(f"  - {q.title}: active={q.is_active}, published={q.is_published}")
    
    # ADD QUESTION COUNT - THIS IS IMPORTANT FOR TEMPLATE
    for quiz in all_quizzes:
        quiz.question_count = Question.query.filter_by(quiz_id=quiz.id).count()
        print(f"    Questions in '{quiz.title}': {quiz.question_count}")
    
    print(f"Sending {len(all_quizzes)} quizzes to template")
    print(f"{'='*60}\n")
    
    return render_template('student_quiz.html', quizzes=all_quizzes)

@student_bp.route('/join', methods=['GET', 'POST'])
def join_by_code():
    """Join quiz by code - NO LOGIN REQUIRED (allows guests)"""
    # CRITICAL: Block only admins, allow students AND guests
    if session.get('role') == 'admin':
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    code = request.args.get('code')
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        return redirect(url_for('student.join_by_link', code=code))
        
    # If authenticated, try to show them dashboard or pre-fill code logic if needed
    # but the form handles everything. No immediate change needed here besides taking POST code.
    
    return render_template('student_quiz.html')


@student_bp.route('/join/<code>', methods=['GET', 'POST'])
def join_by_link(code):
    """Join quiz by link - NO LOGIN REQUIRED (allows guests)"""
    # CRITICAL: Block only admins, allow students AND guests
    if session.get('role') == 'admin':
        flash('Admins are not allowed to attempt quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    quiz = Quiz.query.filter_by(
        join_code=code.upper(), is_published=True
    ).first()
    
    if not quiz:
        return render_template('quiz_closed.html', message='Quiz not found or not published.')

    # ISSUE 1: If user is ALREADY logged in as a student, bypass the name form
    if session.get('username') and session.get('role') == 'student':
        if quiz.is_active:
            return redirect(url_for('student.attempt_quiz', quiz_id=quiz.id))
        else:
            return redirect(url_for('student.waiting_room', quiz_id=quiz.id))
        
    if request.method == 'POST':
        player_name = request.form.get('player_name', '').strip()
        if not player_name:
            flash('Player name cannot be empty.', 'error')
            return render_template('join_quiz.html', quiz=quiz)
            
        session['username'] = player_name
        session['role'] = 'student'
        session['user_id'] = -1  # Guest identifier
        
        # Determine redirect destination based on quiz state
        if quiz.is_active:
            return redirect(url_for('student.attempt_quiz', quiz_id=quiz.id))
        else:
            return redirect(url_for('student.waiting_room', quiz_id=quiz.id))
    
    return render_template('join_quiz.html', quiz=quiz)


@student_bp.route('/waiting-room/<int:quiz_id>')
def waiting_room(quiz_id):
    """Waiting room before quiz starts - NO LOGIN REQUIRED (allows guests)"""
    # CRITICAL: Block only admins, allow students AND guests
    if session.get('role') == 'admin':
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    ensure_guest_student()
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # If admin already started it, redirect to the actual quiz
    if quiz.is_active:
        return redirect(url_for('student.attempt_quiz', quiz_id=quiz.id))
    
    return render_template('waiting_room.html', quiz=quiz)

@student_bp.route('/test-waiting-room/<int:quiz_id>')
def test_waiting_room(quiz_id):
    """Test waiting room directly"""
    quiz = Quiz.query.get_or_404(quiz_id)
    return f"Waiting room test successful! Quiz: {quiz.title}, ID: {quiz.id}"


@student_bp.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    """
    Attempt quiz - NO LOGIN REQUIRED (allows guests)
    CRITICAL FIX: This route should NEVER redirect to admin dashboard
    LEADERBOARD FIX: Clear old data when quiz starts, only show current quiz data
    SEPARATION UPDATE: After answer submission, redirect to separate leaderboard page
    """
    print(f"=== ATTEMPT_QUIZ CALLED ===")
    print(f"Quiz ID: {quiz_id}")
    print(f"Method: {request.method}")
    print(f"Session role: {session.get('role')}")
    print(f"Session user_id: {session.get('user_id')}")
    
    # CRITICAL: Block ONLY admins, allow students AND guests
    if session.get('role') == 'admin':
        flash('Admins cannot solve quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Ensure guest session
    ensure_guest_student()
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # CRITICAL: If quiz is not active, redirect to waiting room
    if not quiz.is_active:
        print(f"Quiz not active, redirecting to waiting room")
        return redirect(url_for('student.waiting_room', quiz_id=quiz.id))
    
    # Check quiz status
    if not quiz.is_published:
        return render_template('quiz_closed.html', message='Quiz has ended or is not available.')
    
    if quiz.is_paused:
        return render_template('quiz_closed.html', message='Quiz is currently paused by admin.')
    
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    
    if not questions:
        return render_template('quiz_closed.html',
                             message='This quiz has no questions yet. Please contact the admin to add questions.')
    
    # Determine student name
    if session.get('user_id') == -1:
        student_name = f"Guest-{session.get('guest_id', '00000000')}"
    else:
        student_name = session['username']
    
    print(f"Student name: {student_name}")
    
    # RETAKE LOGIC
    if request.method == 'GET' and request.args.get('retake') == '1':
        Result.query.filter_by(quiz_id=quiz_id, student=student_name).delete()
        PartialAnswer.query.filter_by(quiz_id=quiz_id, student=student_name).delete()
        db.session.commit()
        flash('Previous attempt cleared. Starting fresh!', 'info')
    
    if request.method == 'POST':
        print('=== POST REQUEST RECEIVED ===')
        print(f'Form data: {dict(request.form)}')
        
        # Get data from form
        qindex = int(request.form.get('qindex', 0))
        question_id = int(request.form.get('question_id'))
        selected_answer = request.form.get('selected_answer')
        
        # FIX: Get time_taken from form (frontend sends it)
        time_taken = int(request.form.get('time_taken', 0))
        
        print(f'Question Index: {qindex}, Question ID: {question_id}')
        print(f"Selected answer: '{selected_answer}'")
        print(f"Time taken from form: {time_taken}s")
        
        current_question = Question.query.get_or_404(question_id)
        print(f"Correct answer: '{current_question.answer}'")
        
        # Check if answer is correct based on question type
        if not selected_answer or selected_answer == 'No Answer':
            is_correct = False
            print('No answer selected - marking as incorrect')
        elif current_question.question_type == 'mcq' or current_question.question_type == 'true_false':
            is_correct = (selected_answer.strip().lower() == current_question.answer.strip().lower())
            print(f"Comparison ({current_question.question_type}): '{selected_answer.strip().lower()}' == '{current_question.answer.strip().lower()}' = {is_correct}")
        elif current_question.question_type == 'checkbox':
            # Checkbox answers are comma-separated strings
            selected_set = set(s.strip().lower() for s in selected_answer.split(',') if s.strip())
            correct_set = set(s.strip().lower() for s in (current_question.answer or '').split(',') if s.strip())
            is_correct = (selected_set == correct_set)
            print(f"Comparison (checkbox): {selected_set} == {correct_set} = {is_correct}")
        elif current_question.question_type == 'short_answer':
            is_correct = (selected_answer.strip().lower() == current_question.answer.strip().lower())
            print(f"Comparison (short_answer): '{selected_answer.strip().lower()}' == '{current_question.answer.strip().lower()}' = {is_correct}")
        else:
            # Fallback
            is_correct = (selected_answer.strip().lower() == current_question.answer.strip().lower())
        
        # Prevent duplicates - use synchronize_session for safety
        db.session.query(PartialAnswer).filter_by(
            quiz_id=quiz_id,
            question_id=question_id,
            student=student_name,
        ).delete(synchronize_session=False)
        db.session.commit()
        
        # Calculate points
        points = PointService.calculate_points(is_correct=is_correct, question_id=current_question.id)
        
        try:
            partial = PartialAnswer(
                quiz_id=quiz_id,
                question_id=question_id,
                student=student_name,
                selected_answer=selected_answer,
                is_correct=is_correct,
                time_taken=time_taken,
                points=points,
                submitted_at=now_utc(),
            )
            db.session.add(partial)
            db.session.commit()
            
            print(f'✓ Saved answer: selected="{selected_answer}", correct={is_correct}, time={time_taken}s, points={points}')
            
            # Update leaderboard - CRITICAL: Only for current quiz
            PointService.update_question_rank_bonuses(quiz_id, question_id)
            
            # Build enriched leaderboard payload
            leaderboard_list = LeaderboardService.build_leaderboard_payload(quiz_id, current_question_id=question_id)
            
            # Add quiz_id to each entry for frontend filtering
            for entry in leaderboard_list:
                entry['quiz_id'] = quiz_id
            
            print(f'Emitting leaderboard_update with {len(leaderboard_list)} students for quiz {quiz_id}')
            
        except Exception as e:
            print(f'ERROR saving answer: {e}')
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        
        # CRITICAL FIX: Check if THIS student has completed the quiz
        total_questions_in_quiz = Question.query.filter_by(quiz_id=quiz_id).count()
        
        # Determine if this is the LAST question based on qindex
        is_last_question = (qindex == total_questions_in_quiz - 1)
        
        # Always emit leaderboard_update for the Admin Real-time board
        # The admin panel will always display it, whereas students only see it if configured
        socketio.emit(
            'leaderboard_update',
            {
                'leaderboard': leaderboard_list,
                'quiz_type_a': quiz.show_leaderboard_each_question,
                'last_submitter': student_name if is_correct else None
            },
            room=f"quiz_{quiz_id}"
        )
        
        # CRITICAL FIX: Only mark quiz as complete if this is the last question for this student
        if is_last_question:
            print(f'=== QUIZ COMPLETE FOR {student_name} ===')
            print(f'This was the last question (index {qindex} of {total_questions_in_quiz-1})')
            
            # Get this student's partial answers
            partials = PartialAnswer.query.filter_by(
                quiz_id=quiz_id, student=student_name
            ).all()
            
            # Calculate this student's score
            score = sum(1 for p in partials if p.is_correct)
            total_time = sum(p.time_taken for p in partials)
            total_points = sum(p.points for p in partials)
            
            print(f'Score: {score}/{total_questions_in_quiz}, Time: {total_time}s, Points: {total_points}')
            
            # Check if result already exists for this student
            existing = Result.query.filter_by(
                quiz_id=quiz_id, student=student_name
            ).first()
            
            # Save final result for this student only
            if not existing:
                result = Result(
                    quiz_id=quiz_id,
                    student=student_name,
                    score=score,
                    total=total_questions_in_quiz,
                    time_taken=total_time,
                    total_points=total_points,
                )
                db.session.add(result)
                db.session.commit()
                print(f'Saved new result for {student_name}')
            else:
                print(f'Result already exists for {student_name}')
            
            print(f'Quiz complete for {student_name}')
            
            # Return completion response
            return jsonify({
                'success': True,
                'is_correct': is_correct,
                'correct_answer': current_question.answer,
                'student_complete': True,
                'score': score,
                'total': total_questions_in_quiz,
                'points': total_points,
                'time': total_time
            })
        else:
            # Student still has more questions to answer
            print(f'Student {student_name} still has more questions (answered {qindex+1} of {total_questions_in_quiz})')
            return jsonify({
                'success': True,
                'is_correct': is_correct,
                'correct_answer': current_question.answer,
                'student_complete': False,
                'next_question': qindex + 1
            })
    
    # ========== GET REQUEST: SHOW QUESTION ==========
    qindex = request.args.get('qindex', type=int)
    
    print(f"GET request - qindex from args: {qindex}")
    
    if qindex is None:
        if quiz.has_timer:
            qindex = quiz_state.get(quiz_id, {}).get('current_qindex', 0)
            print(f"Timer quiz - using quiz_state qindex: {qindex}")
        else:
            qindex = 0
            print(f"Normal quiz - using qindex: 0")
    
    total_questions = len(questions)
    
    print(f"Total questions: {total_questions}, Current qindex: {qindex}")
    
    # CRITICAL FIX: When qindex >= total_questions, redirect to results
    if qindex >= total_questions:
        print(f"Quiz complete - redirecting to results")
        if not quiz.has_timer:
            return redirect(url_for('student.result', quiz_id=quiz_id))
        else:
            return redirect(url_for('student.leaderboard_live', quiz_id=quiz_id, qindex='done'))
    
    current_q = questions[qindex]
    current_question = {
        'id': current_q.id,
        'question': current_q.question,
        'option1': current_q.option1,
        'option2': current_q.option2,
        'option3': current_q.option3,
        'option4': current_q.option4,
        'answer': current_q.answer,
        'correct_answer': current_q.answer,
        'time_limit': current_q.time_limit,
        'points': current_q.points or 10,
        'question_type': current_q.question_type or 'mcq',
    }
    
    template_name = 'attempt_quiz.html' if quiz.has_timer else 'normal_attempt_quiz.html'
    
    # ─────────────────────────────────────────────────────────────
    # SERVER-AUTHORITATIVE TIMER TIMESTAMP
    #
    # quiz_state[quiz_id]["question_started_at"] is set by the server
    # when the admin clicks "Start" or "Next Question" — never by the
    # student and never from Flask session.
    #
    # Fallback: if quiz_state is missing (e.g. server restart mid-quiz)
    # we embed 0 so the frontend falls back to the full time_limit,
    # which is better than embedding time.time() (which would compute
    # ~0 s elapsed and show the full timer anyway, but is semantically
    # misleading and wastes a call to time.time()).
    # ─────────────────────────────────────────────────────────────
    q_started_at = quiz_state.get(quiz_id, {}).get('question_started_at', 0)
    # server_now is passed alongside question_started_at so the client
    # can compute clock_offset = server_now - Date.now()/1000 and correct
    # for device clocks that are ahead of or behind the server.
    server_now = time.time()

    print(f"Rendering template: {template_name} | qindex={qindex} | "
          f"q_started_at={q_started_at:.3f} | server_now={server_now:.3f}")

    return render_template(
        template_name,
        quiz=quiz,
        current_question=current_question,
        total_questions=total_questions,
        current_index=qindex,
        quiz_id=quiz_id,
        question_started_at=q_started_at,
        server_time=server_now,
        quiz_state=quiz_state,
    )

@student_bp.route('/quiz/result/<int:quiz_id>')
def result(quiz_id):
    """Quiz result - NO LOGIN REQUIRED (allows guests)"""
    # CRITICAL: Block only admins
    if session.get('role') == 'admin':
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    ensure_guest_student()
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    student_name = (
        f"Guest-{session.get('guest_id', '00000000')}"
        if session.get('user_id') == -1
        else session['username']
    )
    
    result_obj = Result.query.filter_by(
        quiz_id=quiz_id,
        student=student_name
    ).first()
    
    partials = PartialAnswer.query.filter_by(
        quiz_id=quiz_id,
        student=student_name
    ).all()
    
    if not partials and not result_obj:
        flash('No quiz attempt found. Please take the quiz first.', 'error')
        return redirect(url_for('student.quizzes'))
    
    if partials:
        score = sum(1 for p in partials if p.is_correct)
        total_points = sum(p.points for p in partials)
        total_time = sum(p.time_taken for p in partials)
        total_questions = Question.query.filter_by(quiz_id=quiz_id).count()
        
        if not result_obj:
            result_obj = Result(
                quiz_id=quiz_id,
                student=student_name,
                score=score,
                total=total_questions,
                time_taken=total_time,
                total_points=total_points
            )
            db.session.add(result_obj)
        else:
            result_obj.score = score
            result_obj.total_points = total_points
            result_obj.time_taken = total_time
        
        db.session.commit()
    
    return render_template(
        'student_result.html',
        quiz=quiz,
        quiz_title=quiz.title,
        quiz_id=quiz_id,
        result=result_obj
    )


@student_bp.route('/leaderboard/live/<int:quiz_id>')
def leaderboard_live(quiz_id):
    """
    Live leaderboard for students - NO LOGIN REQUIRED (allows guests)
    SEPARATION UPDATE: Now a completely separate page from quiz attempt
    Shows leaderboard after each question and waits for host to advance
    """
    print(f"\n{'='*60}")
    print("LEADERBOARD LIVE PAGE")
    print(f"{'='*60}")
    
    # CRITICAL: Block only admins
    if session.get('role') == 'admin':
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    ensure_guest_student()
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get qindex from URL (can be 'done' or a number)
    qindex = request.args.get('qindex', '0')
    
    # Determine quiz status
    if qindex == 'done':
        quiz_status = 'done'
        current_qindex = 0  # Doesn't matter when done
        print("Quiz Status: COMPLETE (done)")
    else:
        quiz_status = 'ongoing'
        try:
            current_qindex = int(qindex)
        except ValueError:
            current_qindex = 0
        print(f"Quiz Status: ONGOING (question {current_qindex})")
    
    print(f"Quiz ID: {quiz_id}")
    print(f"QIndex from URL: {qindex}")
    print(f"Current QIndex: {current_qindex}")
    print(f"{'='*60}\n")
    
    return render_template(
        'admin_live_leaderboard.html',
        quiz_id=quiz_id,
        current_qindex=current_qindex,
        quiz_status=quiz_status
    )


@student_bp.route('/leaderboard/<int:quiz_id>')
def leaderboard(quiz_id):
    """Final leaderboard - NO LOGIN REQUIRED (allows guests)"""
    # CRITICAL: Block only admins
    if session.get('role') == 'admin':
        flash('Admins cannot join quizzes ❌', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    ensure_guest_student()
    
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    total_questions = len(questions)
    current_question = questions[0] if questions else None
    
    return render_template(
        'student_result.html',
        quiz=quiz,
        quiz_id=quiz_id,
        quiz_title=quiz.title,
        qindex='done',
        total_questions=total_questions,
        is_last=True,
        result=None,
        current_question=current_question,
    )


@student_bp.route('/history')
@require_student
def history():
    """Student quiz history - REQUIRES LOGIN"""
    username = session.get('username')
    quiz_history = (
        Result.query
        .filter_by(student=username)
        .order_by(Result.submitted_at.desc())
        .all()
    )
    return render_template('student_history.html', history=quiz_history)


# ========================================
# API ENDPOINTS
# ========================================

@student_bp.route('/api/leaderboard/<int:quiz_id>')
def api_leaderboard(quiz_id):
    """
    API: Get leaderboard data
    CRITICAL FIX: Only return data for the specified quiz_id
    Used by the separated leaderboard page to fetch initial data
    """
    print(f"\n{'='*60}")
    print(f"API LEADERBOARD REQUEST")
    print(f"{'='*60}")
    print(f"Quiz ID: {quiz_id}")
    
    # Build leaderboard ONLY for this quiz
    leaderboard_data = LeaderboardService.build_leaderboard_payload(quiz_id)
    
    # Add quiz_id to each entry for frontend filtering
    for entry in leaderboard_data:
        entry['quiz_id'] = quiz_id
    
    # Sort: most points first, then most correct, then least time
    leaderboard_data.sort(key=lambda x: (-x['points'], -x['correct'], x['time']))
    
    print(f'Returning {len(leaderboard_data)} entries for quiz {quiz_id}')
    print(f"{'='*60}\n")
    
    return jsonify({
        'quiz_id': quiz_id,
        'participants': len(leaderboard_data),
        'leaderboard': leaderboard_data,
    })

# Add this at the bottom of student.py
@student_bp.route('/review/<int:quiz_id>')
def review_quiz(quiz_id):
    """
    Page for students to review their answers (Correct/Wrong).
    Fixed to use student name string to match the rest of the app.
    """
    # 1. Identify the student name (matches attempt_quiz logic)
    if session.get('user_id') == -1:
        student_name = f"Guest-{session.get('guest_id', '00000000')}"
    else:
        student_name = session.get('username')
        
    if not student_name:
        flash("Please join the quiz first.", "warning")
        return redirect(url_for('student.quizzes'))

    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.id).all()
    
    # 2. Get answers using the 'student' column (not student_id)
    student_answers = PartialAnswer.query.filter_by(
        quiz_id=quiz_id, 
        student=student_name  # Corrected from student_id
    ).all()
    
    # 3. Map question_id to the option selected
    # PartialAnswer doesn't store the exact text string of the selected option, so we cannot show exactly WHAT they answered, 
    # but we DO know if it was correct or wrong. For a basic review, we'll map is_correct instead.
    answers_map = {ans.question_id: {'is_correct': ans.is_correct, 'time_taken': ans.time_taken} for ans in student_answers}
    
    return render_template('student_review.html', 
                           quiz=quiz, 
                           questions=questions, 
                           answers_map=answers_map)
    
@student_bp.route('/final-leaderboard/<int:quiz_id>')
def final_leaderboard(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template(
        'student_final_leaderboard.html',
        quiz_id=quiz_id,
        quiz=quiz
    )
   
@student_bp.route('/api/question-leaderboard/<int:quiz_id>/<int:question_id>')
def api_question_leaderboard(quiz_id, question_id):
    """
    API: Get question leaderboard
    CRITICAL FIX: Only return data for the specified quiz_id and question_id
    """
    leaderboard_data = LeaderboardService.get_question_leaderboard(quiz_id, question_id)
    
    # Add quiz_id to each entry
    for entry in leaderboard_data:
        entry['quiz_id'] = quiz_id
        entry['question_id'] = question_id
    
    print(f'API Question Leaderboard for quiz {quiz_id}, question {question_id}: {len(leaderboard_data)} entries')
    
    return jsonify({
        'quiz_id': quiz_id,
        'question_id': question_id,
        'participants': len(leaderboard_data),
        'leaderboard': leaderboard_data,
    })


@student_bp.route('/quiz_summary/<int:quiz_id>')
@require_student
def quiz_summary(quiz_id):
    """
    Detailed summary of a completed quiz attempt for a student.
    """
    username = session.get('username')
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        flash("This quiz has been deleted by the admin.", "warning")
        return redirect(url_for('student.history'))

    # Get the final result for this student and quiz
    result_obj = Result.query.filter_by(
        quiz_id=quiz_id, student=username
    ).first()

    if not result_obj:
        flash("Result not found. Make sure you have completed this quiz.", "warning")
        return redirect(url_for('student.history'))

    # Fetch all questions for this quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()

    # Fetch the student's partial answers
    student_answers_list = PartialAnswer.query.filter_by(
        quiz_id=quiz_id, student=username
    ).all()

    # Calculate some additional metrics for the template
    total_time_str = f"{int(result_obj.time_taken // 60):02d}:{int(result_obj.time_taken % 60):02d}"
    
    # We map answers by question ID for easy template access
    answers_map = {}
    for ans in student_answers_list:
        answers_map[ans.question_id] = {
            'selected_answer': ans.selected_answer,
            'is_correct': ans.is_correct,
            'time_taken': ans.time_taken,
        }

    return render_template(
        'student_quiz_summary.html',
        quiz=quiz,
        result=result_obj,
        questions=questions,
        answers_map=answers_map,
        total_time_str=total_time_str
    )