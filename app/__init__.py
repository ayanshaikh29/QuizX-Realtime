"""
Application Factory
Creates and configures the Flask application
"""

from flask import Flask
from app.config import get_config
from app.extensions import db, socketio, migrate, oauth
from sqlalchemy import text
import pytz


def create_app(config_name=None):
    """
    Application factory pattern
    Creates and configures Flask app
    """

    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # ----------------------------
    # Load configuration
    # ----------------------------
    if config_name:
        from app.config import config
        app.config.from_object(config[config_name])
    else:
        app.config.from_object(get_config())

    # ----------------------------
    # Initialize Extensions
    # ----------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)

    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get(
            'SOCKETIO_CORS_ALLOWED_ORIGINS', "*"
        ),
        async_mode=app.config.get(
            'SOCKETIO_ASYNC_MODE', "threading"
        )
    )

    # Add pytz to Jinja globals
    app.jinja_env.globals['pytz'] = pytz

    # ----------------------------
    # Register Blueprints
    # ----------------------------
    from app.routes import auth_bp, admin_bp, student_bp, chatbot_bp, admin_api_bp, admin_groups_bp
    from app.routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_groups_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(public_bp)
    app.register_blueprint(chatbot_bp, url_prefix='/api')
    app.register_blueprint(admin_api_bp)

    # ----------------------------
    # Register Socket Events
    # ----------------------------
    from app.sockets import register_socket_events
    with app.app_context():
        register_socket_events()

    # ----------------------------
    # 🔥 TEMP DATABASE FIX FOR RENDER
    # ----------------------------
    # This ensures missing columns are added automatically
    # Safe to keep, but can be removed after migration stabilizes
    with app.app_context():
        try:
            db.session.execute(text("""
                ALTER TABLE quiz
                ADD COLUMN IF NOT EXISTS show_leaderboard_each_question BOOLEAN DEFAULT FALSE;
            """))

            db.session.execute(text("""
                ALTER TABLE quiz
                ADD COLUMN IF NOT EXISTS timer_mode VARCHAR(50);
            """))

            db.session.execute(text("""
                ALTER TABLE quiz
                ADD COLUMN IF NOT EXISTS total_quiz_time INTEGER;
            """))
            
            db.session.execute(text("""
                ALTER TABLE partial_answer
                ADD COLUMN IF NOT EXISTS selected_answer VARCHAR(255);
            """))

            db.session.execute(text("""
                ALTER TABLE "user"
                ADD COLUMN IF NOT EXISTS email VARCHAR(120) UNIQUE;
            """))

            # Create group table if not exists (must be before adding FK)
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS "group" (
                    id SERIAL PRIMARY KEY,
                    group_name VARCHAR(100) NOT NULL,
                    description VARCHAR(500) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            # Create group_student table if not exists
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS group_student (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    UNIQUE(group_id, student_id),
                    FOREIGN KEY (group_id) REFERENCES "group"(id),
                    FOREIGN KEY (student_id) REFERENCES "user"(id)
                );
            """))

            # Add group_id column to quiz (after group table exists)
            db.session.execute(text("""
                ALTER TABLE quiz
                ADD COLUMN IF NOT EXISTS group_id INTEGER;
            """))

            db.session.commit()
            print(">>> Database columns verified/added")

        except Exception as e:
            db.session.rollback()
            print(">>> DB Auto Fix Error:", e)

    return app