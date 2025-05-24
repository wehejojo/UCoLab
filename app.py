from flask import Flask, render_template, request, url_for, redirect
from typing import Dict, List
import string, random, json

app = Flask(__name__)
users: Dict[str, List[str]] = {
    "names": []
}
SERVER_IP: str = '192.168.0.226' 

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters + string.digits
    code: str = ''.join(random.choice(characters) for _ in range(length))
    return code.upper()

session_code: str = f"{generateRandomSessionCode(4)}"

def userIsTheServer(addr: str) -> bool:
    return addr == SERVER_IP


# WEB ROUTES

@app.route('/')
def home():
    if userIsTheServer(request.remote_addr):
        return f"{session_code}"
    else:
        return render_template('') # USER SESSION CODE PROMPT

@app.route('/login', methods=['POST'])
def userLogin():
    name: str = request.form.get('name')
    users["names"].append(name)

    with open('moment.json', 'w') as file:
        json.dump(users, file, indent=2)

    return redirect(url_for('begin_session'))

@app.route('/submit_code', methods=['POST'])
def submitSessionCode():
    user_input_code: str = request.form.get('session_code')
    if user_input_code == session_code:
        return redirect(url_for()) # USER LOGIN PAGE
    else:
        return "WRONG SESSION CODE!!!"

@app.route(f'/{session_code}')
def begin_session():
    return render_template(
        'index.html' if userIsTheServer(request.remote_addr) else 'admin.html', 
        users=users
    )



if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    )
