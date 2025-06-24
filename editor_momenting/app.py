from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from ot import InsertOp, DeleteOp
from eventlet.semaphore import Semaphore
from collections import defaultdict

import os
import json

# App Setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Constants
BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "group_data.json")
SAVE_INTERVAL = 0.5  # Currently unused

# In-memory state
documents = {}            # group_name -> list of lines
histories = {}            # group_name -> list of ops
client_revisions = {}     # sid -> revision index
client_groups = {}        # sid -> group_name
write_lock = Semaphore()


# ------------- Helper Functions --------------

def get_group_file(group):
    return os.path.join(BASE_DIR, f'document_{group}.json')


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            raw = json.load(f)
            return defaultdict(lambda: {"text": "", "rev": 0}, raw)
    return defaultdict(lambda: {"text": "", "rev": 0})

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(dict(group_data), f, indent=2)
        print(f"[Saved] group_data written to {DATA_FILE}")
    except Exception as e:
        print(f"[Error saving data]: {e}")


def load_document(file_path):
    if not os.path.exists(file_path):
        return [""]
    with open(file_path, 'r') as f:
        data = json.load(f)
    return [data[key] for key in sorted(data.keys(), key=lambda k: int(k.replace("line", "")))]


def save_document(lines, file_path):
    formatted = {f"line{idx+1}": line.replace('\n', '') for idx, line in enumerate(lines)}
    with open(file_path, 'w') as f:
        json.dump(formatted, f, indent=2)


def load_group(group):
    file_path = get_group_file(group)
    documents[group] = [line if isinstance(line, str) else "" for line in load_document(file_path)]
    histories[group] = []


# ------------- Routes --------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/doc/<group_name>')
def generate_doc(group_name):
    return render_template('index.html', group_name=group_name)


# ------------- Socket.IO Events --------------

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    group = request.args.get('group')

    if not group:
        emit('error', {'message': 'Missing group parameter'})
        return

    if group not in documents:
        load_group(group)

    client_groups[sid] = group
    client_revisions[sid] = len(histories[group])

    emit('init', {
        'text': "\n".join(documents[group]),
        'rev': len(histories[group])
    })


@socketio.on('operation')
def handle_operation(data):
    global group_data

    sid = request.sid
    group = client_groups.get(sid)
    print(group)
    if not group:
        return

    base_rev = data.get('rev', 0)
    op_type = data.get('type')
    line = data.get('line')
    col = data.get('col')
    char = data.get('char')

    op = InsertOp(line, col, char) if op_type == 'insert' else DeleteOp(line, col)

    print(base_rev, op_type, line, col, char, op)

    for i in range(base_rev, len(histories[group])):
        op = op.transform_against(histories[group][i])
        if op is None:
            return

    documents[group] = op.apply(documents[group])

    with write_lock:
        save_document(documents[group], get_group_file(group))

        group_data[group] = {
            "text": "\n".join(documents[group]),
            "rev": len(histories[group]) + 1
        }
        save_data()

    histories[group].append(op)
    client_revisions[sid] = len(histories[group])

    emit('remote_op', {
        'type': op_type,
        'line': op.line,
        'col': op.col,
        'char': getattr(op, 'char', None),
        'rev': len(histories[group])
    }, broadcast=True, include_self=False)


@socketio.on('cursor')
def handle_cursor(data):
    data['sid'] = request.sid
    emit('cursor_update', data, broadcast=True, include_self=False)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    client_groups.pop(sid, None)
    client_revisions.pop(sid, None)

@socketio.on('*')
def catch_all(event, data):
    print(f"Received unhandled event: {event} with data: {data}")


# ------------- Main Entry --------------
group_data = load_data()
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
