from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if admin:
        print(f"Admin Username: {admin.username}")
        # Passwords are hashed, so I'll create a temporary admin for testing if needed
        # but let's see if there's any obvious one.
    else:
        print("No admin user found.")
