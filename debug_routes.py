import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app import create_app

app = create_app()
with app.app_context():
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
