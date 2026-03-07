"""
Production WSGI Entry Point
Used by gunicorn and other WSGI servers
"""

from dotenv import load_dotenv
load_dotenv()

import os
import socket

from app import create_app
from app.extensions import socketio


# Create Flask app
app = create_app()


def get_free_port(default_port=5000):
    """
    Check if port is free.
    If not, automatically switch to another port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.bind(("0.0.0.0", default_port))
        sock.close()
        return default_port
    except OSError:
        sock.close()
        print(f">>> Port {default_port} busy, switching to 5050")
        return 5050


# Development server
if __name__ == "__main__":

    # Use PORT from environment or default
    env_port = int(os.getenv("PORT", 5000))

    # Auto resolve port conflict
    port = get_free_port(env_port)

    print(">>> Database columns verified/added")
    print(f">>> Starting QuizX server on http://0.0.0.0:{port}")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True,
        use_reloader=False,  # Important for Windows stability
        allow_unsafe_werkzeug=True
    )