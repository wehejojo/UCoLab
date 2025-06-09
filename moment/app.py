from flask import Flask, render_template, request, session, redirect, url_for, current_app
from flask_socketio import SocketIO, emit
from datetime import timedelta

import string, random

participants_list = []
participants_length = len(participants_list)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.permanent_session_lifetime = timedelta(minutes=30)

socketio = SocketIO(app, cors_allowed_origins="*")

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters.upper() + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

SESSION_CODE: str = generateRandomSessionCode(4)

@app.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    return render_template('/admin/index.html')

@app.route('/master/session', methods=['GET', 'POST'])
def masterSession():
    if request.method == 'POST':
        return redirect(url_for('masterMatch'))
    return render_template('/admin/master_session.html', session_code=SESSION_CODE)

@app.route('/master/match', methods=['GET', 'POST'])
def masterMatch():
    if request.method == 'POST':
        # return redirect(url_for('sessionPage', session_code=SESSION_CODE))
        pass
    return render_template('/admin/match.html', session_code=SESSION_CODE)

@app.route('/mode-select', methods=['GET', 'POST'])
def modeSelect():
    if request.method == 'POST':
        user_code = request.form.get('code')
        
        if not user_code:
            return render_template('error.html', error_message="Please enter a code.")
        
        if user_code == SESSION_CODE:
            return redirect(url_for('sessionPage', session_code=SESSION_CODE))
        else:
            return render_template('error.html', error_message="Wrong Code!!")
    
    return render_template('/client/mode_select.html')

@app.route('/session/<session_code>')
def sessionPage(session_code):
    return render_template(
        '/client/match.html',
        session_code=session_code,
        participants=participants_list,
        length=len(participants_list)
    )

@app.route('/<session_code>/quiz')
def quiz(session_code):
    return render_template(
        '/client/quiz.html',
        session_code=session_code
    )



@socketio.on('connect')
def handle_connect():
    emit('update', {
        'participants': participants_list,
        'count': len(participants_list)
    })

@socketio.on('join')
def handle_join(data):
    participants_list.append(data)
    emit('update', {
        'participants': participants_list,
        'count': len(participants_list)
    }, broadcast=True)

@socketio.on('start_matching')
def handle_start_matching():
    with current_app.app_context():
        quiz_url = url_for('quiz', session_code=SESSION_CODE)
    emit('redirect_to_quiz',{
        'url': quiz_url
    }, broadcast=True)


if __name__ == '__main__':
    socketio.run(
        app=app,
        host='0.0.0.0',
        port=5000,
        debug=True
    )
