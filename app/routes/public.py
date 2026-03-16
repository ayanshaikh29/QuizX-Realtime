from flask import Blueprint, redirect, url_for, session, flash, send_from_directory, current_app
from app.models import Quiz
import os

public_bp = Blueprint('public', __name__)


@public_bp.route('/favicon.ico')
def favicon():
    """Serve favicon with long cache headers to prevent flash on navigation"""
    return send_from_directory(
        os.path.join(current_app.root_path, '..', 'static'),
        'favicon.png',
        mimetype='image/png',
        max_age=31536000  # 1 year cache
    )
