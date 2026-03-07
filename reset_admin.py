from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='admin', role='admin').first()
    if user:
        user.password = generate_password_hash('admin123')
        db.session.commit()
        print("Admin password reset to 'admin123'")
    else:
        print("Admin user not found.")
