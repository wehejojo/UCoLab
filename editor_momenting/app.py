# 👇 MUST BE FIRST
import eventlet
eventlet.monkey_patch()

# Now you can import the rest
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

shared_document = {
    "time": 0,
    "blocks": [],
    "version": "2.26.5"
}

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    emit("load_doc", shared_document)

@socketio.on("update_doc")
def handle_update(data):
    global shared_document
    if "blocks" in data and isinstance(data["blocks"], list):
        shared_document = data
        emit("doc_updated", data, broadcast=True, include_self=False)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
