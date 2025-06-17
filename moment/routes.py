from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, current_app, jsonify
)
from moment import socketio
from flask_socketio import emit
from moment.matchUsers import run_matching

import string, random, os, json

main = Blueprint('main', __name__)

participants_list = []
participants_length = len(participants_list)

DB = os.path.join(os.path.dirname(__file__), 'db', 'answers.json')
GROUPS = os.path.join(os.path.dirname(__file__), 'db', 'groups.json')

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters.upper() + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

SESSION_CODE: str = generateRandomSessionCode(4)

def load_json_file(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

def save_json_file(filename, data):
    existing = load_json_file(filename)
    if existing == data:
        print("Data unchanged. Skipping write.")
        return
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def all_questions_answered(user_data):
    if 'answers' not in user_data:
        return False
    return all(f'q{i}' in user_data['answers'] for i in range(1, 6))

@main.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    return render_template('/admin/index.html')

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
    db = load_json_file(DB)
    participants = [{
        'name': name,
        'college': info.get('college', ''),
        'skills': info.get('skills', '')
    } for name, info in db.items()]
    return render_template('/client/match.html', session_code=session_code,
                           participants=participants, length=len(participants))

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

    db = load_json_file(DB)
    if name not in db:
        db[name] = {}
    if 'answers' not in db[name]:
        db[name]['answers'] = {}
    db[name]['answers'][question_id] = answer
    save_json_file(DB, db)

    return jsonify({'success': True, 'message': 'Answer submitted successfully'})

@main.route('/quiz/group', methods=['GET'])
def groups():
    return render_template('/client/groups.html', session_code=SESSION_CODE)

@main.route('/match', methods=['POST'])
def match_users():
    db = load_json_file(DB)
    gps = load_json_file(GROUPS)

    incomplete_users = [
        name for name, data in db.items()
        if not all_questions_answered(data)
    ]

    if incomplete_users:
        return jsonify({
            'error': 'Not all users have completed the quiz',
            'incomplete_users': incomplete_users
        }), 400

    if db:
        groups = run_matching(db)
        if groups:
            if groups != gps:
                print("New group structure detected. Overwriting saved groups.")
                save_json_file(GROUPS, groups)
            else:
                print("Groups unchanged. Skipping file write.")

            return jsonify({"success": True, "groups": groups}), 200
        return jsonify({'error': 'Unable to form any groups'}), 400
    return jsonify({'error': 'No users found'}), 400

@main.route('/getGroups', methods=['GET'])
def get_groups():
    name = request.args.get("name")
    groups = load_json_file(GROUPS)

    if not groups:
        return jsonify({"success": False, "error": "No groups available yet"}), 404

    user_group = None
    for group_name, group_data in groups.items():
        for member in group_data["members"].values():
            if member.get("name") == name:
                user_group = {group_name: group_data}
                break
        if user_group:
            break

    if user_group:
        return jsonify({
            "success": True,
            "groups": user_group,
            "currentuser": name
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": "User not found in any group"
        }), 404

# -------------------- Socket.IO Events -------------------- #

@socketio.on('connect')
def handle_connect():
    db = load_json_file(DB)
    participants = [{
        'name': name,
        'college': info.get('college', ''),
        'skills': info.get('skills', '')
    } for name, info in db.items()]
    emit('update', {'participants': participants, 'count': len(participants)})

@socketio.on('join')
def handle_join(data):
    name = data.get('name')
    college = data.get('college')
    skills = data.get('skills')

    db = load_json_file(DB)
    if name not in db:
        db[name] = {'college': college, 'skills': skills}
    save_json_file(DB, db)

    participants_list.append(data)

    emit('update', {
        'participants': [
            {'name': n, 'college': d['college'], 'skills': d['skills']}
            for n, d in db.items()
        ],
        'count': len(db)
    }, broadcast=True)

@socketio.on('start_matching')
def handle_start_matching():
    with current_app.app_context():
        quiz_url = url_for('main.quiz', session_code=SESSION_CODE)
    emit('redirect_to_quiz', {'url': quiz_url}, broadcast=True)