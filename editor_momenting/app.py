import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

shared_document = {
    "time": 0,
    "blocks": [],
    "version": "2.26.5"
}

connected_users = {}

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    user_id = str(uuid.uuid4())
    connected_users[request.sid] = user_id
    emit("load_doc", shared_document)
    print(f"User {user_id} connected")

@socketio.on("disconnect")
def handle_disconnect():
    user_id = connected_users.pop(request.sid, None)
    if user_id:
        emit("cursor_update", {"user_id": user_id, "top": -9999, "left": -9999}, broadcast=True)
        print(f"User {user_id} disconnected")

@socketio.on("update_doc")
def handle_update(data):
    global shared_document
    if "blocks" in data and isinstance(data["blocks"], list):
        shared_document = data
        emit("doc_updated", data, broadcast=True, include_self=False)

@socketio.on("cursor_move")
def handle_cursor_move(pos):
    user_id = connected_users.get(request.sid)
    if user_id:
        emit("cursor_update", {
            "user_id": user_id,
            "top": pos.get("top", 0),
            "left": pos.get("left", 0)
        }, broadcast=True, include_self=False)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
