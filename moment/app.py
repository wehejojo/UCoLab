from flask import Flask, render_template, request, session, redirect, url_for
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Use a secure key in production
app.permanent_session_lifetime = timedelta(minutes=30)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session.permanent = True
        session['name'] = request.form['name']
        session['age'] = request.form['age']
        return redirect(url_for('result'))

    return render_template('index.html')

@app.route('/result')
def result():
    name = session.get('name', 'Unknown')
    age = session.get('age', 'Unknown')
    return f"<h1>Hello, {name}!</h1><p>You are {age} years old.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
