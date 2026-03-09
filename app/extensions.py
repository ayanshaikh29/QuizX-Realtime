"""
Flask Extensions
Centralized extension initialization
"""

from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth

# Initialize extensions (without app binding)

db = SQLAlchemy()
oauth = OAuth()

# Force threading mode to avoid eventlet issues on Windows
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading",   # VERY IMPORTANT (fixes port conflicts)
    logger=False,
    engineio_logger=False
)

migrate = Migrate()


# Global state dictionaries (managed by services)
quiz_state = {}
active_participants = {}