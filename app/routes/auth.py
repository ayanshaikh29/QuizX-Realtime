"""
Authentication Routes
Handles login, logout, registration, profile
"""
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, oauth
from app.models import User
from app.utils.helpers import get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Homepage"""
    return render_template('index.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not password or role not in ['admin', 'student']:
            flash('Invalid input', 'error')

        elif User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')

        else:
            user = User(
                username=username,
                password=generate_password_hash(password),
                role=role,
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))

        return render_template('login.html', mode='register')

    return render_template('login.html', mode='register')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login
    Supports Google-Form style redirect using session['next_url']
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        user = User.query.filter_by(username=username, role=role).first()

        if not user:
            flash('User not found or role mismatch', 'error')

        elif not check_password_hash(user.password, password):
            flash('Incorrect password', 'error')

        else:
            # ✅ Create session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            flash('Login successful!', 'success')

            # If user came from join link, redirect back there
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)

            # Normal dashboard redirect
            return redirect(
                url_for('admin.dashboard')
                if user.role == 'admin'
                else url_for('student.dashboard')
            )

        return render_template('login.html', mode='login')

    return render_template('login.html', mode='login')


@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.index'))


@auth_bp.route('/google-login')
def google_login():
    """Initiate Google OAuth login"""
    try:
        google = oauth.create_client('google')
        redirect_uri = url_for('auth.google_callback', _external=True)
        nonce = secrets.token_urlsafe(16)   # ✅ Generate nonce
        session['oauth_nonce'] = nonce      # ✅ Store nonce in session
        return google.authorize_redirect(redirect_uri, nonce=nonce)  # ✅ Pass nonce to Google
    except Exception as e:
        flash(f'Failed to initiate Google login: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/google-callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        google = oauth.create_client('google')
        token = google.authorize_access_token()

        nonce = session.pop('oauth_nonce', None)               # ✅ Retrieve stored nonce
        user_info = google.parse_id_token(token, nonce=nonce)  # ✅ Pass nonce for verification

        if not user_info:
            flash('Failed to retrieve user info from Google.', 'error')
            return redirect(url_for('auth.login'))

        email = user_info.get('email')

        # ✅ Extract real name from Google, fallback to given_name, then a default
        name = (
            user_info.get('name')
            or user_info.get('given_name')
            or "Google User"
        )

        if not email:
            flash('Google account must have an email attached.', 'error')
            return redirect(url_for('auth.login'))

        # ✅ Look up existing user by email first
        user = User.query.filter_by(email=email).first()

        # ✅ Fallback: check by username = email (legacy/migration accounts)
        if not user:
            user = User.query.filter_by(username=email).first()

        if not user:
            # ✅ New user — store real name as username, not email
            user = User(
                username=name,
                email=email,
                role='student',
                password=generate_password_hash('google_oauth_no_password')  # Placeholder
            )
            db.session.add(user)
            db.session.commit()
            flash(f'Welcome to QuizX, {name}!', 'success')
        else:
            # ✅ Existing user — keep their username, only patch missing email
            if not user.email:
                user.email = email
                db.session.commit()
            flash(f'Welcome back, {user.username}!', 'success')

        # ✅ Store correct username (real name) in session
        session['user_id'] = user.id
        session['username'] = user.username  # will be real name, not email
        session['role'] = user.role

        return redirect(
            url_for('admin.dashboard')
            if user.role == 'admin'
            else url_for('student.dashboard')
        )

    except Exception as e:
        flash(f'Login failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
def profile():
    """User profile page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('profile.html', user=user)


@auth_bp.route('/quizzes')
def redirect_quizzes():
    """Redirect /quizzes to /student/quizzes"""
    return redirect(url_for('student.quizzes'))


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_username = request.form.get('username')

        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Username already taken!', 'error')
            else:
                user.username = new_username
                session['username'] = new_username
                flash('Profile updated!', 'success')

        db.session.commit()
        return redirect(url_for('auth.profile'))

    return render_template('edit_profile.html', user=user)