"""
Socket.IO Event Handlers
Real-time quiz events and leaderboard updates
"""
from flask import session, request
from flask_socketio import emit, join_room, leave_room
from app.extensions import db, socketio, quiz_state
from app.models import Quiz, Question, PartialAnswer
from app.services.point_service import PointService
from app.services.leaderboard_service import LeaderboardService
# Store waiting room participants
waiting_rooms = {}
active_participants = {}

def register_socket_events():
    """Register all Socket.IO event handlers"""
    
    @socketio.on('join_quiz')
    def join_quiz(data):
        """Student joins a quiz room"""
        quiz_id = str(data['quiz_id'])
        room_name = f"quiz_{quiz_id}"
        join_room(room_name)
        print(f'✅ User joined room: {room_name}')
    
    @socketio.on('admin_next_question')
    def admin_next_question(data):
        """Admin advances to next question"""
        quiz_id = int(data['quiz_id'])
        room_name = f"quiz_{quiz_id}"
        
        if quiz_id not in quiz_state:
            quiz_state[quiz_id] = {'current_qindex': 0}
        
        total_questions = Question.query.filter_by(quiz_id=quiz_id).count()
        current_index = quiz_state[quiz_id]['current_qindex']
        
        print(f'🎯 Current question: {current_index + 1} of {total_questions}')
        
        quiz = Quiz.query.get(quiz_id)
        if current_index >= total_questions - 1:
            print('🏁 Quiz finished - emitting quiz_finished event')
            socketio.emit('quiz_finished', {}, room=room_name)
            return
        
        quiz_state[quiz_id]['current_qindex'] += 1
        new_qindex = quiz_state[quiz_id]['current_qindex']
        
        print(f'📤 Moving to question {new_qindex + 1} of {total_questions}')
        socketio.emit(
            'load_next_question',
            {'qindex': new_qindex, 'quiz_id': quiz_id},
            room=room_name
        )
        print(f'📡 Emitted load_next_question with qindex={new_qindex} to room {room_name}')
    
    @socketio.on('admin_stop_quiz')
    def admin_stop_quiz(data):
        """Admin stops quiz and redirects everyone to final leaderboard"""
        quiz_id = int(data['quiz_id'])
        room_name = f"quiz_{quiz_id}"
        print(f'🛑 Admin stopped quiz {quiz_id}. Redirecting to final leaderboard.')
        
        from app.models import Quiz
        from app.extensions import db
        quiz = Quiz.query.get(quiz_id)
        if quiz:
            quiz.is_active = False
            db.session.commit()
            
        socketio.emit(
            'quiz_stopped',
            {'quiz_id': quiz_id},
            room=room_name
        )
        print(f'📡 Emitted quiz_stopped to room {room_name}')
    
    @socketio.on('join_waiting_room')
    def handle_join_waiting_room(data):
        """Student joins waiting room"""
        quiz_id = str(data.get('quiz_id'))
        username = data.get('username') or session.get('username') or f"Guest-{session.get('guest_id', '00000000')}"
        
        # Create waiting room if it doesn't exist
        if quiz_id not in waiting_rooms:
            waiting_rooms[quiz_id] = []
        
        # Add user if not already there
        if username not in waiting_rooms[quiz_id]:
            waiting_rooms[quiz_id].append(username)
            print(f'👤 {username} joined waiting room for quiz {quiz_id}')
        
        # Join the socket room for this waiting room
        join_room(f'waiting_room_{quiz_id}')
        
        # Broadcast updated participant list to everyone in waiting room
        emit('update_participants', {
            'users': waiting_rooms[quiz_id],
            'count': len(waiting_rooms[quiz_id])
        }, room=f'waiting_room_{quiz_id}')
        
        # Also update active participants for the main quiz room
        join_room(quiz_id)  # Join main quiz room too
        if quiz_id not in active_participants:
            active_participants[quiz_id] = {}
        active_participants[quiz_id][request.sid] = username
    
    @socketio.on('leave_waiting_room')
    def handle_leave_waiting_room(data):
        """Student leaves waiting room"""
        quiz_id = str(data.get('quiz_id'))
        username = data.get('username') or session.get('username') or f"Guest-{session.get('guest_id', '00000000')}"
        
        if quiz_id in waiting_rooms and username in waiting_rooms[quiz_id]:
            waiting_rooms[quiz_id].remove(username)
            print(f'👤 {username} left waiting room for quiz {quiz_id}')
            
            # Broadcast updated list
            emit('update_participants', {
                'users': waiting_rooms[quiz_id],
                'count': len(waiting_rooms[quiz_id])
            }, room=f'waiting_room_{quiz_id}')
            
            # Remove from active participants
            if quiz_id in active_participants:
                for sid, name in list(active_participants[quiz_id].items()):
                    if name == username:
                        del active_participants[quiz_id][sid]
                        break
    
    @socketio.on('disconnect')
    def handle_disconnect(reason=None):
        """Handle user disconnect"""
        # Clean up from waiting rooms
        for quiz_id in list(waiting_rooms.keys()):
            for username in waiting_rooms[quiz_id]:
                if request.sid in active_participants.get(quiz_id, {}):
                    if active_participants[quiz_id].get(request.sid) == username:
                        waiting_rooms[quiz_id].remove(username)
                        emit('update_participants', {
                            'users': waiting_rooms[quiz_id],
                            'count': len(waiting_rooms[quiz_id])
                        }, room=f'waiting_room_{quiz_id}')
                        break
        
        # Clean up from active participants
        for quiz_id in active_participants:
            if request.sid in active_participants[quiz_id]:
                del active_participants[quiz_id][request.sid]
                emit_participant_update(quiz_id)
                break


def emit_participant_update(quiz_id):
    """Emit updated participant list"""
    # Get unique names for the list
    names = list(set(active_participants.get(quiz_id, {}).values()))
    socketio.emit('update_participants', {
        'count': len(names),
        'users': names
    }, room=f"quiz_{quiz_id}")