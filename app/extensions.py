"""
Flask Extensions
Centralized extension initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
# Initialize extensions (without app binding)
db = SQLAlchemy()
socketio = SocketIO()
migrate = Migrate()
# Global state dictionaries (will be managed by services)
quiz_state = {}
active_participants = {}