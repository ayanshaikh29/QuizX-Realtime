from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random, string

# ================== APP CONFIG ==================
app = Flask(__name__)
app.secret_key = "quizx_secret_key_change_later"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================== UTILS ==================
def generate_join_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ================== MODELS ==================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer)  # minutes
    start_time = db.Column(db.DateTime)

    is_locked = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)

    join_code = db.Column(db.String(10), unique=True)

    # Pause support
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    paused_seconds = db.Column(db.Integer, default=0)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)

    question = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, nullable=False)
    student = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================== DB INIT ==================
with app.app_context():
    db.create_all()

# ================== HOME ==================
@app.route("/")
def index():
    return render_template("index.html")

# ================== AUTH ==================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"]).first():
            error = "Username already exists"
        else:
            user = User(
                username=request.form["username"],
                password=generate_password_hash(request.form["password"]),
                role=request.form["role"]
            )
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("register.html", error=error)

# ================== LOGIN ==================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form.get("username"),
            role=request.form.get("role")
        ).first()

        if not user:
            error = "User not found or role mismatch"
        elif not check_password_hash(user.password, request.form.get("password")):
            error = "Incorrect password"
        else:
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            return redirect(
                url_for("admin_dashboard")
                if user.role == "admin"
                else url_for("student_dashboard")
            )

    return render_template("login.html", error=error)

# ================== LOGOUT ==================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ================== ADMIN ==================
@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")

# ================== PROFILE ==================
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    return render_template("profile.html", user=user)

# ================== EDIT_PROFILE ==================
@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user = get_current_user()  # however you fetch the logged-in user
    if request.method == "POST":
        # Update user info here
        user.name = request.form['name']
        user.email = request.form['email']
        db.session.commit()
        return redirect(url_for('profile'))
    return render_template("edit_profile.html", user=user)


@app.route("/admin/quizzes", methods=["GET", "POST"])
def admin_quizzes():
    if request.method == "POST":
        quiz = Quiz(
            title=request.form["title"],
            duration=int(request.form["duration"])
        )
        db.session.add(quiz)
        db.session.commit()

    quizzes = Quiz.query.all()
    return render_template("admin_quiz.html", quizzes=quizzes)


@app.route("/admin/add-question/<int:quiz_id>", methods=["GET", "POST"])
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.is_active:
        return redirect(url_for("admin_quizzes"))

    if request.method == "POST":
        questions = request.form.getlist("question[]")

        for i, qtext in enumerate(questions):
            ans = request.form.get(f"answer_{i}")
            if not ans:
                continue

            q = Question(
                quiz_id=quiz_id,
                question=qtext,
                option1=request.form.get(f"option1_{i}"),
                option2=request.form.get(f"option2_{i}"),
                option3=request.form.get(f"option3_{i}"),
                option4=request.form.get(f"option4_{i}"),
                answer=request.form.get(f"option{ans}_{i}")
            )
            db.session.add(q)

        db.session.commit()
        return redirect(url_for("add_question", quiz_id=quiz_id))

    return render_template("add_question.html", quiz=quiz)


@app.route("/admin/end-questions/<int:quiz_id>")
def end_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_locked = True
    db.session.commit()
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/publish-quiz/<int:quiz_id>")
def publish_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    quiz.is_published = True
    quiz.is_active = True
    quiz.start_time = datetime.utcnow()
    quiz.paused_seconds = 0
    quiz.is_paused = False

    if not quiz.join_code:
        quiz.join_code = generate_join_code()

    db.session.commit()
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/pause-quiz/<int:quiz_id>")
def pause_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and not quiz.is_paused:
        quiz.is_paused = True
        quiz.paused_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/resume-quiz/<int:quiz_id>")
def resume_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.is_active and quiz.is_paused:
        paused_time = (datetime.utcnow() - quiz.paused_at).total_seconds()
        quiz.paused_seconds += int(paused_time)
        quiz.is_paused = False
        quiz.paused_at = None
        db.session.commit()
    return redirect(url_for("admin_quizzes"))


@app.route("/admin/stop-quiz/<int:quiz_id>")
def stop_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.is_active = False
    db.session.commit()
    return redirect(url_for("admin_quizzes"))

# ================== JOIN QUIZ ==================
@app.route("/join", methods=["GET", "POST"])
def join_by_code():
    error = None
    if request.method == "POST":
        code = request.form["code"].upper()
        quiz = Quiz.query.filter_by(join_code=code, is_active=True).first()

        if quiz:
            return redirect(url_for("attempt_quiz", quiz_id=quiz.id))

        error = "Quiz is not active or code invalid"

    return render_template("join.html", error=error)


@app.route("/join/<code>")
def join_by_link(code):
    quiz = Quiz.query.filter_by(join_code=code.upper(), is_active=True).first()

    if not quiz:
        return render_template("quiz_closed.html", message="Quiz session has ended")

    return redirect(url_for("attempt_quiz", quiz_id=quiz.id))

# ================== STUDENT ==================
@app.route("/student/dashboard")
def student_dashboard():
    return render_template("student_dashboard.html", user=session.get("username"))


@app.route("/student/quizzes")
def student_quizzes():
    quizzes = Quiz.query.filter_by(is_active=True).all()
    return render_template("student_quiz.html", quizzes=quizzes)


@app.route("/student/quiz/<int:quiz_id>", methods=["GET", "POST"])
def attempt_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if not quiz.is_active:
        return render_template("quiz_closed.html", message="Quiz has ended")

    if quiz.is_paused:
        return render_template("quiz_closed.html", message="Quiz is paused")

    end_time = quiz.start_time + timedelta(minutes=quiz.duration)
    end_time += timedelta(seconds=quiz.paused_seconds)
    remaining_seconds = int((end_time - datetime.utcnow()).total_seconds())

    if remaining_seconds <= 0:
        quiz.is_active = False
        db.session.commit()
        return render_template("quiz_closed.html", message="Quiz time is over")

    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if request.method == "POST":
        score = sum(
            1 for q in questions if request.form.get(str(q.id)) == q.answer
        )

        result = Result(
            quiz_id=quiz_id,
            student=session.get("username"),
            score=score,
            total=len(questions)
        )
        db.session.add(result)
        db.session.commit()

        return redirect(url_for("leaderboard", quiz_id=quiz_id))

    return render_template(
        "attempt_quiz.html",
        questions=questions,
        remaining_seconds=remaining_seconds
    )

# ================== LEADERBOARD ==================
@app.route("/leaderboard/<int:quiz_id>")
def leaderboard(quiz_id):
    results = Result.query.filter_by(quiz_id=quiz_id)\
        .order_by(Result.score.desc(), Result.submitted_at.asc())\
        .all()

    return render_template("scoreboard.html", results=results)

# ================== RUN ==================
if __name__ == "__main__":
    app.run(debug=True)
