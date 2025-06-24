from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, current_app, jsonify
)
from moment import socketio
from flask_socketio import emit

from moment.matchUsers import run_matching
from moment.models import db, User, Answer, Group, GroupMembership

import string, random

main = Blueprint('main', __name__)

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters.upper() + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

SESSION_CODE: str = generateRandomSessionCode(4)

def all_questions_answered(user_data):
    if 'answers' not in user_data:
        return False
    return all(f'q{i}' in user_data['answers'] for i in range(1, 6))

@main.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    users = User.query.all()
    return render_template('/admin/index.html', users = users)

@main.route('/master/session', methods=['GET', 'POST'])
def masterSession():
    if request.method == 'POST':
        return redirect(url_for('main.masterMatch'))
    return render_template('/admin/master_session.html', session_code=SESSION_CODE)

@main.route('/master/match', methods=['GET'])
def masterMatch():
    return render_template('/admin/match.html', session_code=SESSION_CODE)

@main.route('/mode-select', methods=['GET', 'POST'])
def modeSelect():
    if request.method == 'POST':
        user_code = request.form.get('code')
        print(user_code)
        if not user_code:
            return render_template('error.html', error_message="Please enter a code.")
        if user_code == SESSION_CODE:
            return redirect(url_for('main.sessionPage', session_code=SESSION_CODE))
        return render_template('error.html', error_message="Wrong Code!!")
    return render_template('/client/mode_select.html')

@main.route('/session/<session_code>')
def sessionPage(session_code):
    users = User.query.all()
    participants = [{
        'name': user.name,
        'college': user.college,
        'skills': user.skills
    } for user in users]
    return render_template(
        '/client/match.html', session_code=session_code, 
        participants=participants, length=len(participants)
    )

@main.route('/master/quiz')
def masterQuiz():
    return render_template('/admin/quiz.html', session_code=SESSION_CODE)

@main.route('/<session_code>/quiz')
def quiz(session_code):
    return render_template('/client/quiz.html', session_code=session_code)

@main.route('/quiz/submit', methods=['POST'])
def submitQuiz():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400

    data = request.get_json()
    name = data.get('name')
    question_id = data.get('question_id')
    answer = data.get('answer')

    if not question_id or not answer or not name:
        return jsonify({'success': False, 'error': 'Missing name, question_id, or answer'}), 400
    
    user = User.query.filter_by(name=name).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    existing_answer = Answer.query.filter_by(
        user_id = user.id,
        question_id = question_id
    ).first()

    if existing_answer:
        existing_answer.answer = answer
    else:
        new_answer = Answer(user_id=user.id, question_id=question_id, answer=answer)
        db.session.add(new_answer)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Answer submitted successfully'})

@main.route('/quiz/group', methods=['GET'])
def groups():
    return render_template('/client/groups.html', session_code=SESSION_CODE)

@main.route('/match', methods=['POST'])
def match_users():
    users = User.query.all()

    db_data = {}
    incomplete_users = []

    for user in users:
        answers = {a.question_id: a.answer for a in user.answers}
        if len(answers) < 5:
            incomplete_users.append(user.name)
            continue

        db_data[user.name] = {
            'college': user.college,
            'skills': user.skills,
            'answers': answers
        }

    if incomplete_users:
        return jsonify({
            'error': 'Not all users have completed the quiz',
            'incomplete_users': incomplete_users
        }), 400
    
    if not db_data:
        return jsonify({'error': 'No users found'}), 400
    
    groups_data = run_matching(db_data)
    if not groups_data:
        return jsonify({'error': 'Unable to form any groups'}), 400
    
    GroupMembership.query.delete()
    Group.query.delete()
    db.session.commit()

    for group_name, group_info in groups_data.items():
        group = Group(name=group_name)
        db.session.add(group)
        db.session.flush()

        for user_data in group_info['members'].values():
            user = User.query.filter_by(name=user_data['name']).first()
            if user:
                membership = GroupMembership(group_id=group.id, user_id=user.id)
                db.session.add(membership)

    db.session.commit()
    return jsonify({"success": True, "groups": groups_data}), 200

@main.route('/getGroups', methods=['GET'])
def get_groups():
    name = request.args.get("name")
    if not name:
        return jsonify({"success": False, "error": "Missing 'name' parameter"}), 400
    
    user = User.query.filter_by(name=name).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    group = (
        db.session.query(Group)
        .join(GroupMembership, Group.id == GroupMembership.group_id)
        .join(User, User.id == GroupMembership.user_id)
        .filter(User.name == name)
        .first()
    )

    if not group:
        return jsonify({"success": False, "error": "User not found in any group"}), 404
    
    members = [
        {
            "name": u.name,
            "college": u.college,
            "skills": u.skills
        }
        for u in db.session.query(User)
        .join(GroupMembership)
        .filter(GroupMembership.group_id == group.id)
        .all()
    ]

    return jsonify({
        "success": True,
        "groups": {
            group.name: {
                "members": {str(i+1): member for i, member in enumerate(members)}
            }
        },
        "currentuser": name
    }), 200

# -------------------- Socket.IO Events -------------------- #

@socketio.on('connect')
def handle_connect():
    users = User.query.all()
    participants = [{
        'name': user.name,
        'college': user.college,
        'skills': user.skills
    } for user in users]

    emit('update', {
        'participants': participants,
        'count': len(participants)
    })

@socketio.on('join')
def handle_join(data):
    name = data.get('name')
    college = data.get('college')
    skills = data.get('skills')

    user = User.query.filter_by(name=name).first()
    if not user:
        user = User(name=name, college=college, skills=skills)
        db.session.add(user)
        db.session.commit()
    
    users = User.query.all()
    participants = [{'name': u.name, 'college': u.college, 'skills': u.skills} for u in users]

    emit('update', {
        'participants': participants,
        'count': len(participants)
    }, broadcast=True)

@socketio.on('start_matching')
def handle_start_matching():
    with current_app.app_context():
        quiz_url = url_for('main.quiz', session_code=SESSION_CODE)
    emit('redirect_to_quiz', {'url': quiz_url}, broadcast=True)