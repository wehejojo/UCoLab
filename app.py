from flask import Flask, render_template, request, url_for, redirect
import string, random, json

app = Flask(__name__)
users = []
SERVER_IP = '192.168.0.226' 

def generateRandomSessionCode(length: int) -> str:
    characters = string.ascii_letters + string.digits
    code = ''.join(random.choice(characters) for _ in range(length))
    return code.upper()

session_code: str = f"{generateRandomSessionCode(7)}"

@app.route('/')
def home():
    return f"{session_code}"

@app.route(f'/{session_code}')
def view():
    user_ip = request.remote_addr
    if user_ip != SERVER_IP:
        return render_template('index.html', users=users)
    else:
        return render_template('admin.html', users=users)

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    users.append(name)
    with open('moment.json', 'a') as file:
        data = users
        json.dump(data, file, indent=2)
    return redirect(url_for('view'))

@app.route('/users')
def user():
    return '  '.join(i for i in users)

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    )