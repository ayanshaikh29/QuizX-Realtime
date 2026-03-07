"""
Group Models
Models for the group management system
"""
from app.extensions import db
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


class Group(db.Model):
    """Group model for organizing students"""
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=now_utc)

    # Relationships
    students = db.relationship('GroupStudent', backref='group', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.group_name}>'


class GroupStudent(db.Model):
    """Association between groups and students"""
    __tablename__ = 'group_student'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationship to User
    student = db.relationship('User', backref='group_memberships', lazy=True)

    # Prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('group_id', 'student_id', name='_group_student_uc'),)

    def __repr__(self):
        return f'<GroupStudent group={self.group_id} student={self.student_id}>'
