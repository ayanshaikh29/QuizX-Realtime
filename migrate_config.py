from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()


def migrate_database():
    with app.app_context():

        print(">>> Starting PostgreSQL migration...")

        queries = [

            """
            ALTER TABLE quiz
            ADD COLUMN IF NOT EXISTS show_leaderboard_each_question BOOLEAN DEFAULT TRUE
            """,

            """
            ALTER TABLE quiz
            ADD COLUMN IF NOT EXISTS timer_mode VARCHAR(20) DEFAULT 'per_question'
            """,

            """
            ALTER TABLE quiz
            ADD COLUMN IF NOT EXISTS total_quiz_time INTEGER
            """,

            """
            ALTER TABLE question
            ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 1
            """,

            """
            ALTER TABLE question
            ADD COLUMN IF NOT EXISTS explanation TEXT
            """

        ]

        try:

            for query in queries:
                db.session.execute(text(query))

            db.session.commit()

            print(">>> Migration successful")

        except Exception as e:
            db.session.rollback()
            print(">>> Migration failed:", e)


if __name__ == "__main__":
    migrate_database()