"""
Admin Groups Routes
CRUD for group management, student assignment, and quiz-group linking
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import User, Quiz, Group, GroupStudent
from app.utils import require_admin

admin_groups_bp = Blueprint('admin_groups', __name__)


@admin_groups_bp.route('/groups')
@require_admin
def groups():
    """List all groups"""
    all_groups = Group.query.order_by(Group.created_at.desc()).all()

    # Build stats for each group
    group_data = []
    for g in all_groups:
        student_count = GroupStudent.query.filter_by(group_id=g.id).count()
        quiz_count = Quiz.query.filter_by(group_id=g.id).count()
        group_data.append({
            'group': g,
            'student_count': student_count,
            'quiz_count': quiz_count,
        })

    return render_template('admin_groups.html', group_data=group_data)


@admin_groups_bp.route('/groups/create', methods=['POST'])
@require_admin
def create_group():
    """Create a new group"""
    name = request.form.get('group_name', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Group name is required.', 'error')
        return redirect(url_for('admin_groups.groups'))

    existing = Group.query.filter_by(group_name=name).first()
    if existing:
        flash('A group with this name already exists.', 'error')
        return redirect(url_for('admin_groups.groups'))

    group = Group(group_name=name, description=description)
    db.session.add(group)
    db.session.commit()
    flash(f'Group "{name}" created successfully!', 'success')
    return redirect(url_for('admin_groups.groups'))


@admin_groups_bp.route('/groups/<int:group_id>')
@require_admin
def view_group(group_id):
    """View group details: students and assigned quizzes"""
    group = Group.query.get_or_404(group_id)

    # Students in this group
    memberships = GroupStudent.query.filter_by(group_id=group_id).all()
    member_ids = [m.student_id for m in memberships]
    members = User.query.filter(User.id.in_(member_ids)).all() if member_ids else []

    # Students NOT in this group (for dropdown)
    available_students = User.query.filter(
        User.role == 'student',
        ~User.id.in_(member_ids) if member_ids else True
    ).order_by(User.username).all()

    # Quizzes assigned to this group
    assigned_quizzes = Quiz.query.filter_by(group_id=group_id).all()

    # Quizzes not assigned to any group (for dropdown)
    available_quizzes = Quiz.query.filter(
        (Quiz.group_id == None) | (Quiz.group_id == group_id)
    ).all()
    unassigned_quizzes = [q for q in available_quizzes if q.group_id is None]

    return render_template(
        'admin_group_detail.html',
        group=group,
        members=members,
        available_students=available_students,
        assigned_quizzes=assigned_quizzes,
        unassigned_quizzes=unassigned_quizzes,
    )


@admin_groups_bp.route('/groups/<int:group_id>/delete')
@require_admin
def delete_group(group_id):
    """Delete a group and unassign its quizzes"""
    group = Group.query.get_or_404(group_id)

    # Unassign all quizzes from this group
    Quiz.query.filter_by(group_id=group_id).update({'group_id': None})

    # Delete group (cascade deletes GroupStudent entries)
    db.session.delete(group)
    db.session.commit()
    flash(f'Group "{group.group_name}" deleted.', 'info')
    return redirect(url_for('admin_groups.groups'))


@admin_groups_bp.route('/groups/<int:group_id>/add_student', methods=['POST'])
@require_admin
def add_student_to_group(group_id):
    """Add a student to the group"""
    group = Group.query.get_or_404(group_id)
    student_id = request.form.get('student_id', type=int)

    if not student_id:
        flash('Please select a student.', 'error')
        return redirect(url_for('admin_groups.view_group', group_id=group_id))

    # Check if already a member
    existing = GroupStudent.query.filter_by(group_id=group_id, student_id=student_id).first()
    if existing:
        flash('Student is already in this group.', 'warning')
        return redirect(url_for('admin_groups.view_group', group_id=group_id))

    membership = GroupStudent(group_id=group_id, student_id=student_id)
    db.session.add(membership)
    db.session.commit()

    student = User.query.get(student_id)
    flash(f'Added "{student.username}" to group "{group.group_name}".', 'success')
    return redirect(url_for('admin_groups.view_group', group_id=group_id))


@admin_groups_bp.route('/groups/<int:group_id>/remove_student/<int:student_id>')
@require_admin
def remove_student_from_group(group_id, student_id):
    """Remove a student from the group"""
    membership = GroupStudent.query.filter_by(
        group_id=group_id, student_id=student_id
    ).first_or_404()

    student = User.query.get(student_id)
    db.session.delete(membership)
    db.session.commit()
    flash(f'Removed "{student.username}" from the group.', 'info')
    return redirect(url_for('admin_groups.view_group', group_id=group_id))


@admin_groups_bp.route('/groups/<int:group_id>/assign_quiz', methods=['POST'])
@require_admin
def assign_quiz_to_group(group_id):
    """Assign a quiz to this group"""
    group = Group.query.get_or_404(group_id)
    quiz_id = request.form.get('quiz_id', type=int)

    if not quiz_id:
        flash('Please select a quiz.', 'error')
        return redirect(url_for('admin_groups.view_group', group_id=group_id))

    quiz = Quiz.query.get_or_404(quiz_id)
    quiz.group_id = group_id
    db.session.commit()

    flash(f'Quiz "{quiz.title}" assigned to group "{group.group_name}".', 'success')
    return redirect(url_for('admin_groups.view_group', group_id=group_id))


@admin_groups_bp.route('/groups/<int:group_id>/unassign_quiz/<int:quiz_id>')
@require_admin
def unassign_quiz_from_group(group_id, quiz_id):
    """Remove a quiz assignment from a group"""
    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.group_id == group_id:
        quiz.group_id = None
        db.session.commit()
        flash(f'Quiz "{quiz.title}" unassigned from the group.', 'info')

    return redirect(url_for('admin_groups.view_group', group_id=group_id))
