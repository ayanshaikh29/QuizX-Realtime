from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# User Table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin or student


# Create DB tables
with app.app_context():
    db.create_all()


# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        user = User.query.filter_by(username=username, role=role).first()

        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['role'] = user.role

            if role == "admin":
                return redirect("/admin")
            else:
                return redirect("/student")

        return "Invalid credentials! Try again."

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        user = User(username=username, password=password, role=role)
        db.session.add(user)
        db.session.commit()

        return "User registered successfully!"

    return render_template("register.html")


@app.route("/admin")
def admin_dashboard():
    if "role" in session and session["role"] == "admin":
        return render_template("admin_dashboard.html", user=session["username"])
    return "Unauthorized access!"


@app.route("/student")
def student_dashboard():
    if "role" in session and session["role"] == "student":
        return render_template("student_dashboard.html", user=session["username"])
    return "Unauthorized access!"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
