from app import create_app
from app.extensions import db
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

app = create_app()

def migrate_database():
    with app.app_context():
        print("Starting PostgreSQL migration...")
        
        queries = [
            ("ALTER TABLE quiz ADD COLUMN show_leaderboard_each_question BOOLEAN DEFAULT TRUE", "quiz.show_leaderboard_each_question"),
            ("ALTER TABLE quiz ADD COLUMN timer_mode VARCHAR(20) DEFAULT 'per_question'", "quiz.timer_mode"),
            ("ALTER TABLE quiz ADD COLUMN total_quiz_time INTEGER", "quiz.total_quiz_time"),
            ("ALTER TABLE question ADD COLUMN points INTEGER DEFAULT 1", "question.points"),
            ("ALTER TABLE question ADD COLUMN explanation TEXT", "question.explanation")
        ]
        
        for query_str, col_name in queries:
            try:
                db.session.execute(text(query_str))
                db.session.commit()
                print(f"Success adding {col_name}")
            except ProgrammingError as e:
                db.session.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print(f"Skipping {col_name}, already exists.")
                else:
                    print(f"Error adding {col_name}: {e}")
            except Exception as e:
                db.session.rollback()
                print(f"Unexpected Error adding {col_name}: {e}")

        print("Migration complete! Database is now updated for Advanced Quiz Configuration.")

if __name__ == "__main__":
    migrate_database()
