from app import create_app
from app.extensions import db
from app.models import User, Quiz
app = create_app()
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if not u:
        u = User(username='admin', role='admin')
        db.session.add(u)
    u.set_password('admin')
    q = Quiz.query.get(24)
    if q:
        q.is_active = True
        q.is_published = True
    db.session.commit()
    print("Admin password set and Quiz 24 activated.")
