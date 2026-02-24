from app import create_app
from app.models import User, Quiz
app = create_app()
with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    quiz = Quiz.query.first()
    print(f"ADMIN_USERNAME: {admin.username if admin else 'None'}")
    print(f"QUIZ_ID: {quiz.id if quiz else 'None'}")
    print(f"JOIN_CODE: {quiz.join_code if quiz else 'None'}")
