import uuid
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from matchUsers import run_matching
from flask import render_template

import string, random, secrets, json, os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(
    app,
    supports_credentials=True,
    origins=["http://192.168.0.87:5500"]
) 

match_status = {
    "started": False
}

DB = 'answers.json'
QUESTIONS = 'questions.json'
SERVER_IP = '192.168.0.87' 
# SERVER_IP = '192.168.0.147'

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
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

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

@app.route('/quiz-redirect' , methods=['GET'])
def quizRedirect():
    global quiz_started
    user_id = session.get('user_id')
    if userIsTheServer(request.remote_addr):
        quiz_started = True
        return jsonify({"success": True, "message": "Quiz started.", "user_id": user_id})
    else:
        return jsonify({"success": quiz_started})

@app.route('/check-matching', methods=['GET'])
def check_matching():
    return jsonify({"started": match_status["started"]})

@app.route('/match', methods=['GET'])
def match_users():
    with open('json/users.json', 'r') as f:
        users = json.load(f)

    groups = run_matching(users)
    return jsonify(groups)

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
    name = data.get('name')
    college = data.get('college')
    attribute = data.get('attribute')
    user_id = session.get('user_id')
    print(user_id)
    
    session['user_id'] = user_id 
    
    db = load_json_file(DB)
    if user_id not in db:
        db[user_id] = {}
        
    print(user_id)
    
    db[user_id]["name"] = name
    db[user_id]["college"] = college
    db[user_id]["attribute"] = attribute
    db[user_id]["skills"] = {}  # Initialize skills object

    save_json_file(DB, db)
    return jsonify({ "success" : True, "data": db })

@app.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.json
    user_id = session.get('user_id')
    question_id = data.get('question_id')
    answer = data.get('answer')
    print("Received answer from user:", session.get('user_id'))
    
    if not user_id or not question_id or not answer:
        return jsonify({'success': False, 'error': 'Invalid data'}), 400

    db = load_json_file(DB)

    if user_id not in db:
        db[user_id] = {"skills": {}}

    if "skills" not in db[user_id]:
        db[user_id]["skills"] = {}

    db[user_id]["skills"][question_id] = answer
    save_json_file(DB, db)
    print("Saved:", db[user_id])  # Optional debug
    return jsonify({'success': True})

@app.route('/toggle-matching', methods=['POST'])
def start_matching():
    global match_status
    match_status["started"] = not match_status["started"]
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    ) 