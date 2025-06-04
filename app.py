from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO
from matchUsers import run_matching

import string, random, secrets, json, os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://192.168.0.87:5500"], manage_session=True)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://192.168.0.87:5500"}})


match_status = {
    "started": False
}

DB = 'answers.json'
GROUPS = 'groups.json'
QUESTIONS = 'questions.json'
SERVER_IP = '192.168.0.87' 

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters.upper() + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def userIsTheServer(addr: str) -> bool:
    return addr == SERVER_IP

SESSION_CODE: str = generateRandomSessionCode(4)

def load_json_file(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

def save_json_file(filename, data):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing = json.load(f)
        if existing == data:
            print("Data unchanged. Skipping write.")
            return
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def all_questions_answered(user_data):
    if 'skills' not in user_data:
        return False
    return all(f'q{i}' in user_data['skills'] for i in range(1, 6))

@app.before_request
def assign_user():
    if 'user_id' not in session:
        session['user_id'] = f"user_{os.urandom(4).hex()}"
        session.permanent = True

@app.route('/')
def index():
    if userIsTheServer(request.remote_addr):
        return jsonify({
            "session_code": SESSION_CODE,
            "secret-key" : app.secret_key,
            "success": True
        })
    return jsonify({ "success": False })

@app.route('/questions', methods=['GET'])
def getQuestions():
    questions = load_json_file(QUESTIONS)
    return jsonify(questions)

@app.route('/status', methods=['GET'])
def getStatus():
    if userIsTheServer(request.remote_addr):
        return jsonify({ "success": True, "is_server": True })
    else:
        return jsonify({ "success": True, "is_server": False })

@app.route('/room_code', methods=['GET'])
def getRoomCode():
    return jsonify({
        "room_code": SESSION_CODE,
        "success": True
    })

@app.route('/show-participants')
def returnParticipantCount():
    db = load_json_file(DB)
    return jsonify({
        "participant-count" : len(db),
        "participants" : db
    })

@app.route('/check-matching', methods=['GET'])
def check_matching():
    return jsonify({"started": match_status["started"]})

@app.route('/match', methods=['GET'])
def match_users():
    db = load_json_file(DB)
    gps = load_json_file(GROUPS)

    # Check if all users have completed all questions
    incomplete_users = [user_id for user_id, data in db.items() if not all_questions_answered(data)]
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

            return jsonify({
                "success": True,
                "groups": groups,
                "userID": session.get('user_id')
            }), 200
        else:
            return jsonify({'error': 'Unable to form any groups'}), 400
    else:
        return jsonify({'error': 'No users found'}), 400

@app.route('/submit-code', methods=['POST'])
def method_name():
    data = request.get_json()
    code = data.get('code')

    if code == SESSION_CODE:
        return jsonify({ 'success' : True, 'redirect_url' : '/room' })
    else:
        return jsonify({ 'success' : False, 'error' : "Invalid Code" })

@app.route('/submit-user-details', methods=['POST'])
def submitUserDetails():
    data = request.get_json()
    user_id = data.get('user_id')  # <-- now explicitly passed
    name = data.get('name')
    college = data.get('college')
    attribute = data.get('attribute')

    if not user_id:
        return jsonify({"success": False, "error": "No user ID"}), 400

    db = load_json_file(DB)
    if user_id not in db:
        db[user_id] = {}

    db[user_id]["name"] = name
    db[user_id]["college"] = college
    db[user_id]["attribute"] = attribute
    if "skills" not in db[user_id]:
        db[user_id]["skills"] = {}

    save_json_file(DB, db)
    return jsonify({"success": True, "data": db})


@app.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    user_id = data.get('user_id')  # Get it from frontend!
    question_id = data.get('question_id')
    answer = data.get('answer')

    
    if not user_id or not question_id or not answer:
        return jsonify({'success': False, 'error': 'Invalid data'}), 400

    db = load_json_file(DB)

    if user_id not in db:
        db[user_id] = {"skills": {}}

    if "skills" not in db[user_id]:
        db[user_id]["skills"] = {}

    db[user_id]["skills"][question_id] = answer
    save_json_file(DB, db)
    return jsonify({'success': True})

@app.route("/toggle-matching", methods=["POST"])
def start_quiz():
    socketio.emit(
        "start_quiz",
        {"type": "start_quiz"},
        namespace='/'
    )
    match_status["started"] = True
    return {"success": True}

@socketio.on('connect')
def handle_connect():
    print("Client connected:", request.sid)

if __name__ == "__main__":
    socketio.run(
        app, host="0.0.0.0", 
        port=5000, debug=True   
    )