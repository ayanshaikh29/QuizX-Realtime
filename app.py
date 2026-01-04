from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import random
import string
import time
import uuid
from functools import wraps


# ================== APP CONFIG ==================
app = Flask(__name__)
app.secret_key = "quizx_secret_key_change_later"  # CHANGE THIS IN PRODUCTION!

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ================== SOCKETIO SETUP ==================
socketio = SocketIO(app, cors_allowed_origins="*")


# ================== HELPERS ==================
def now_utc():
    return datetime.now(timezone.utc)


def generate_join_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_current_user():
    if "user_id" not in session or session.get("user_id") == -1:
        return None
    return User.query.get(session["user_id"])


def calculate_points(is_correct, time_taken=None, time_limit=None, rank=None, has_timer=False):
    """
    Calculate points based on correctness, speed (if timer enabled), and rank.
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


def update_question_rank_bonuses(quiz_id, question_id):
    """
    Update rank bonuses for all correct answers to a question.
    """
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return

    # Get all correct answers for this question, ordered by time (if timer) or submission time
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
        # For non-timer quizzes, order by submission time only
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
        new_points = calculate_points(
            is_correct=True,
            time_taken=partial.time_taken,
            time_limit=question.time_limit if quiz.has_timer else None,
            rank=rank,
            has_timer=quiz.has_timer,
        )
        partial.points = new_points

    db.session.commit()


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def require_student(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "student":
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def ensure_guest_student():
    if "user_id" not in session:
        session["role"] = "student"
        if "username" not in session:
            session["username"] = "Guest"
        if "user_id" not in session:
            session["user_id"] = -1
        # Unique guest ID
        if "guest_id" not in session:
            session["guest_id"] = str(uuid.uuid4())[:8]


# ================== MODELS ==================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    has_timer = db.Column(db.Boolean, default=False)  # Timer enabled or not
    start_time = db.Column(db.DateTime)
    is_locked = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    join_code = db.Column(db.String(10), unique=True)
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    paused_seconds = db.Column(db.Integer, default=0)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    order = db.Column(db.Integer, default=0)
    question = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    time_limit = db.Column(db.Integer, default=30)  # Only used if quiz.has_timer=True


class PartialAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, nullable=False, index=True)
    question_id = db.Column(db.Integer, nullable=False, index=True)
    student = db.Column(db.String(100), nullable=False, index=True)
    is_correct = db.Column(db.Boolean, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)  # Always track time
    points = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=now_utc)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, nullable=False)
    student = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)
    total_points = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=now_utc)


# ================== INIT DB ==================
with app.app_context():
    db.create_all()


# ================== AUTH ==================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or role not in ["admin", "student"]:
            flash("Invalid input", "error")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
        else:
            user = User(
                username=username,
                password=generate_password_hash(password),
                role=role,
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        user = User.query.filter_by(username=username, role=role).first()

        if not user:
            flash("User not found or role mismatch", "error")
        elif not check_password_hash(user.password, password):
            flash("Incorrect password", "error")
        else:
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            flash("Login successful!", "success")
            return redirect(
                url_for("admin_dashboard" if user.role == "admin" else "student_dashboard")
            )

        return render_template("login.html")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("index"))


# ================== ADMIN ==================
@app.route("/admin/dashboard")
@require_admin
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/admin/quizzes", methods=["GET", "POST"])
@require_admin
def admin_quizzes():
    if request.method == "POST":
        title = request.form.get("title")
        quiz_type = request.form.get("quiz_type")  # 'normal' or 'timer'

        if not title:
            flash("Quiz title is required", "error")
            return redirect(url_for("admin_quizzes"))

        has_timer = (quiz_type == "timer")
        quiz = Quiz(title=title, has_timer=has_timer)
        db.session.add(quiz)
        db.session.commit()
        flash(
            f"{'Timer-based' if has_timer else 'Normal'} quiz created successfully! Now add questions.",
            "success",
        )
        # Redirect to add questions page for the newly created quiz
        return redirect(url_for("add_question", quiz_id=quiz.id))

    quizzes = Quiz.query.all()
    return render_template("admin_quiz.html", quizzes=quizzes)


@app.route("/admin/add-question/<int:quiz_id>", methods=["GET", "POST"])
@require_admin
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active:
        flash("Cannot add questions to an active quiz.", "error")
        return redirect(url_for("admin_quizzes"))

    if request.method == "POST":
        questions_data = request.form.getlist("question[]")
        added = False
        for i, qtext in enumerate(questions_data):
            if not qtext.strip():
                continue
            ans_index = request.form.get(f"answer_{i}")
            if not ans_index:
                continue
            option_key = f"option{ans_index}_{i}"
            correct_answer = request.form.get(option_key)
            if not correct_answer:
                continue

            # Only get time_limit if quiz has timer
            if quiz.has_timer:
                time_str = request.form.get(f"time_{i}", "30")
                try:
                    time_limit = max(5, int(time_str))
                except ValueError:
                    time_limit = 30
            else:
                time_limit = 0  # No timer for normal quiz

            q = Question(
                quiz_id=quiz_id,
                order=i + 1,
                question=qtext,
                option1=request.form.get(f"option1_{i}", ""),
                option2=request.form.get(f"option2_{i}", ""),
                option3=request.form.get(f"option3_{i}", ""),
                option4=request.form.get(f"option4_{i}", ""),
                answer=correct_answer,
                time_limit=time_limit,
            )
            db.session.add(q)
            added = True

        if added:
            db.session.commit()
            flash("Questions added successfully!", "success")
        else:
            flash("No valid questions were added.", "warning")
        return redirect(url_for("add_question", quiz_id=quiz_id))
    
    # === CORRECTION START ===
    # Check if quiz has timer or not and select template
    if quiz.has_timer:
        template_name = "add_question.html"
    else:
        template_name = "normal_add_question.html"

    # Use the selected template_name variable
    return render_template(template_name, quiz=quiz)
    # === CORRECTION END ===


@app.route("/admin/end-questions/<int:quiz_id>")
@require_admin
def end_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_locked = True
    db.session.commit()
    flash("Question adding locked.", "info")
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/publish-quiz/<int:quiz_id>")
@require_admin
def publish_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not quiz.is_locked:
        flash("Lock questions first before publishing!", "error")
        return redirect(url_for("admin_quizzes"))

    quiz.is_published = True
    quiz.is_active = True
    quiz.start_time = now_utc()
    quiz.paused_seconds = 0
    quiz.is_paused = False
    if not quiz.join_code:
        quiz.join_code = generate_join_code()

    db.session.commit()
    flash(f"Quiz published! Join code: {quiz.join_code}", "success")
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/pause-quiz/<int:quiz_id>")
@require_admin
def pause_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and not quiz.is_paused:
        quiz.is_paused = True
        quiz.paused_at = now_utc()
        db.session.commit()
        flash("Quiz paused.", "info")
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/resume-quiz/<int:quiz_id>")
@require_admin
def resume_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and quiz.is_paused:
        paused_time = (now_utc() - quiz.paused_at).total_seconds()
        quiz.paused_seconds += int(paused_time)
        quiz.is_paused = False
        quiz.paused_at = None
        db.session.commit()
        flash("Quiz resumed.", "info")
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/stop-quiz/<int:quiz_id>")
@require_admin
def stop_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_active = False
    db.session.commit()
    flash("Quiz stopped.", "info")
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/live-leaderboard/<int:quiz_id>")
@require_admin
def admin_live_leaderboard(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    total_questions = len(questions)
    return render_template(
        "admin_live_leaderboard.html",
        quiz=quiz,
        quiz_id=quiz_id,
        qindex="live",
        total_questions=total_questions,
        is_last=False,
    )


# ================== STUDENT DASHBOARD (LOGIN REQUIRED) ==================
@app.route("/student/dashboard")
@require_student
def student_dashboard():
    return render_template("student_dashboard.html", username=session.get("username"))


# ================== PUBLIC / GUEST ACCESS ROUTES (NO LOGIN REQUIRED) ==================
@app.route("/student/quizzes")
def student_quizzes():
    ensure_guest_student()
    quizzes = Quiz.query.filter_by(is_active=True, is_published=True).all()
    return render_template("student_quiz.html", quizzes=quizzes)


@app.route("/join", methods=["GET", "POST"])
def join_by_code():
    ensure_guest_student()

    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        quiz = Quiz.query.filter_by(
            join_code=code, is_active=True, is_published=True
        ).first()
        if quiz:
            return redirect(url_for("attempt_quiz", quiz_id=quiz.id))
        flash("Invalid or inactive quiz code.", "error")
    return render_template("student_quiz.html")


@app.route("/join/<code>")
def join_by_link(code):
    ensure_guest_student()
    quiz = Quiz.query.filter_by(
        join_code=code.upper(), is_active=True, is_published=True
    ).first()

    if not quiz:
        return render_template("quiz_closed.html", message="Quiz not found or not active.")

    return redirect(url_for("attempt_quiz", quiz_id=quiz.id))


@app.route("/student/quiz/<int:quiz_id>", methods=["GET", "POST"])
def attempt_quiz(quiz_id):
    ensure_guest_student()
    quiz = Quiz.query.get_or_404(quiz_id)

    if not quiz.is_active or not quiz.is_published:
        return render_template("quiz_closed.html", message="Quiz has ended or is not available.")

    if quiz.is_paused:
        return render_template("quiz_closed.html", message="Quiz is currently paused by admin.")

    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()

    # Unique student name
    if session.get("user_id") == -1:
        student_name = f"Guest-{session.get('guest_id', '00000000')}"
    else:
        student_name = session["username"]

    start_key = f"quiz_start_{quiz_id}"

    if start_key not in session:
        session[start_key] = time.time()

    if request.method == "POST":
        print("=== POST REQUEST RECEIVED ===")
        print(f"Form data: {dict(request.form)}")

        action = request.form.get("start_question")
        if action == "1":
            # Start question timer
            question_id = int(request.form.get("question_id"))
            q_start_key = f"q_start_{quiz_id}_{question_id}"
            if q_start_key not in session:
                session[q_start_key] = time.time()
            return jsonify({"success": True})

        # Per-question submission
        qindex = int(request.form.get("qindex", 0))
        question_id = int(request.form.get("question_id"))
        selected_answer = request.form.get("selected_answer")

        print(f"Question Index: {qindex}, Question ID: {question_id}")
        print(f"Selected answer: '{selected_answer}'")

        q_start_key = f"q_start_{quiz_id}_{question_id}"
        q_start_ts = session.get(q_start_key, time.time())
        time_taken = int(time.time() - q_start_ts)

        current_question = Question.query.get_or_404(question_id)

        print(f"Correct answer: '{current_question.answer}'")

        # If no answer selected, mark as incorrect
        if not selected_answer:
            is_correct = False
            print("No answer selected - marking as incorrect")
        else:
            # Compare with stripped values to avoid whitespace issues
            is_correct = (selected_answer.strip() == current_question.answer.strip())
            print(
                f"Comparison: '{selected_answer.strip()}' == '{current_question.answer.strip()}' = {is_correct}"
            )

        # Prevent duplicates
        PartialAnswer.query.filter_by(
            quiz_id=quiz_id,
            question_id=question_id,
            student=student_name,
        ).delete()
        db.session.commit()

        # Calculate points for this question
        question_points = 0
        if is_correct:
            time_limit = current_question.time_limit if quiz.has_timer else None
            question_points = calculate_points(
                is_correct,
                time_taken,
                time_limit,
                has_timer=quiz.has_timer,
            )

        # Save partial answer with points
        try:
            partial = PartialAnswer(
                quiz_id=quiz_id,
                question_id=question_id,
                student=student_name,
                is_correct=is_correct,
                time_taken=time_taken,
                points=question_points,
                submitted_at=now_utc(),
            )
            db.session.add(partial)
            db.session.commit()
            print(
                f"✓ Saved answer: correct={is_correct}, time={time_taken}s, points={question_points}"
            )

            # Update rank bonuses and emit only if correct
            if is_correct:
                update_question_rank_bonuses(quiz_id, question_id)
                socketio.emit(
                    "question_leaderboard_update",
                    {
                        "quiz_id": quiz_id,
                        "question_id": question_id,
                    },
                    room=str(quiz_id),
                )

        except Exception as e:
            print(f"ERROR saving answer: {e}")
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

        next_qindex = qindex + 1
        total_questions = len(questions)
        is_last = next_qindex >= total_questions

        if is_last:
            # Calculate final score and total points
            partials = PartialAnswer.query.filter_by(
                quiz_id=quiz_id, student=student_name
            ).all()
            score = sum(1 for p in partials if p.is_correct)
            total_time = sum(p.time_taken for p in partials)
            total_points = sum(p.points for p in partials)
            total = total_questions

            print("=== QUIZ COMPLETE ===")
            print(
                f"Score: {score}/{total}, Time: {total_time}s, Points: {total_points}"
            )

            # Save final result for all (guests and logged-in)
            existing = Result.query.filter_by(
                quiz_id=quiz_id, student=student_name
            ).first()
            if not existing:
                result = Result(
                    quiz_id=quiz_id,
                    student=student_name,
                    score=score,
                    total=total,
                    time_taken=total_time,
                    total_points=total_points,
                )
                db.session.add(result)
                db.session.commit()

            session.pop(start_key, None)
            socketio.emit(
                "leaderboard_refresh", {"quiz_id": quiz_id}, room=str(quiz_id)
            )

            # Full session cleanup for this quiz
            for k in list(session.keys()):
                if k.startswith(f"q_start_{quiz_id}_") or k == start_key:
                    session.pop(k, None)

            return jsonify(
                {
                    "success": True,
                    "is_last": True,
                    "is_correct": is_correct,
                    "time_taken": time_taken,
                    "score": score,
                    "total": total,
                    "total_time": total_time,
                    "next_qindex": total_questions,
                }
            )

        print(f"=== CONTINUING TO QUESTION {next_qindex} ===")

        return jsonify(
            {
                "success": True,
                "is_last": False,
                "is_correct": is_correct,
                "time_taken": time_taken,
                "next_qindex": next_qindex,
            }
        )

    # GET: Show current question
    qindex = request.args.get("qindex", 0, type=int)
    total_questions = len(questions)
    if qindex >= total_questions:
        # Quiz complete, redirect to leaderboard
        return redirect(url_for("leaderboard_live", quiz_id=quiz_id, qindex="done"))

    current_q = questions[qindex]
    current_question = {
        "id": current_q.id,
        "question": current_q.question,
        "option1": current_q.option1,
        "option2": current_q.option2,
        "option3": current_q.option3,
        "option4": current_q.option4,
        "time_limit": current_q.time_limit,
    }

    # Render different templates based on quiz type
    if quiz.has_timer:
        template_name = "attempt_quiz.html"
    else:
        template_name = "normal_attempt_quiz.html"

    return render_template(
        template_name,
        quiz=quiz,
        current_question=current_question,
        total_questions=total_questions,
        current_index=qindex,
        quiz_id=quiz_id,
    )


# ================== LEADERBOARD ==================
@app.route("/leaderboard/live/<int:quiz_id>")
def leaderboard_live(quiz_id):
    ensure_guest_student()
    qindex = request.args.get("qindex", 0, type=str)
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    total_questions = len(questions)

    # Check if it's the last question or done
    try:
        qindex_int = int(qindex) if qindex != "done" else total_questions
    except Exception:
        qindex_int = 0

    is_last = (qindex == "done" or qindex_int >= total_questions)

    return render_template(
        "admin_live_leaderboard.html",
        quiz=quiz,
        quiz_id=quiz_id,
        qindex=qindex,
        total_questions=total_questions,
        is_last=is_last,
    )


@app.route("/leaderboard/<int:quiz_id>")
def leaderboard(quiz_id):
    ensure_guest_student()
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order).all()
    total_questions = len(questions)

    # Use the same template with is_last=True to show final results
    return render_template(
        "admin_live_leaderboard.html",
        quiz=quiz,
        quiz_id=quiz_id,
        qindex="done",
        total_questions=total_questions,
        is_last=True,
    )


@app.route("/api/leaderboard/<int:quiz_id>")
def api_leaderboard(quiz_id):
    # Get all partial answers to calculate total points
    from sqlalchemy import func

    # Calculate total points per student
    points_query = db.session.query(
        PartialAnswer.student,
        func.sum(PartialAnswer.points).label("total_points"),
        func.sum(
            db.case((PartialAnswer.is_correct == True, 1), else_=0)
        ).label("correct_count"),
        func.sum(PartialAnswer.time_taken).label("total_time"),
    ).filter_by(quiz_id=quiz_id).group_by(PartialAnswer.student).all()

    # Get total questions
    total_questions = Question.query.filter_by(quiz_id=quiz_id).count()

    # Sort by points (desc), then score (desc), then time (asc)
    leaderboard_data = sorted(
        [(p.student, p.total_points, p.correct_count, p.total_time) for p in points_query],
        key=lambda x: (-x[1], -x[2], x[3]),
    )

    return jsonify(
        {
            "participants": len(leaderboard_data),
            "leaderboard": [
                {
                    "student": row[0],
                    "points": row[1],
                    "score": row[2],
                    "total": total_questions,
                    "time": row[3],
                }
                for row in leaderboard_data
            ],
        }
    )


@app.route("/api/question-leaderboard/<int:quiz_id>/<int:question_id>")
def api_question_leaderboard(quiz_id, question_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.has_timer:
        partials = PartialAnswer.query.filter_by(
            quiz_id=quiz_id,
            question_id=question_id,
            is_correct=True,
        ).order_by(
            PartialAnswer.time_taken.asc(),
            PartialAnswer.submitted_at.asc(),
        ).limit(10).all()
    else:
        partials = PartialAnswer.query.filter_by(
            quiz_id=quiz_id,
            question_id=question_id,
            is_correct=True,
        ).order_by(
            PartialAnswer.submitted_at.asc(),
        ).limit(10).all()

    return jsonify(
        {
            "participants": len(partials),
            "leaderboard": [
                {
                    "rank": idx + 1,
                    "student": p.student,
                    "time_taken": p.time_taken,
                    "points": p.points,
                }
                for idx, p in enumerate(partials)
            ],
        }
    )


# ================== SOCKETIO EVENTS ==================
@socketio.on("join_quiz")
def join_quiz(data):
    quiz_id = str(data["quiz_id"])
    join_room(quiz_id)


# ================== PROFILE (OPTIONAL - REQUIRES LOGIN) ==================
@app.route("/profile")
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("profile.html", user=user)


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        new_username = request.form.get("username")
        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash("Username already taken!", "error")
            else:
                user.username = new_username
                session["username"] = new_username
                flash("Profile updated!", "success")
        db.session.commit()
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user)


# ================== RUN ==================
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)