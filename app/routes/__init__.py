"""
Routes Package
Exports all route blueprints
"""
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.student import student_bp
from app.routes.chatbot import chatbot_bp
from app.routes.admin_api import admin_api_bp
from app.routes.admin_groups import admin_groups_bp


__all__ = ['auth_bp', 'admin_bp', 'student_bp', 'chatbot_bp', 'admin_api_bp', 'admin_groups_bp']