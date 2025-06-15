from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from dataclasses import dataclass
import json
import os
import eventlet
from ot import InsertOp, DeleteOp
from eventlet.semaphore import Semaphore

import time

last_save_time = time.time()
SAVE_INTERVAL = 0.5  

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DOC_FILE = 'document.json'

def save_document(lines):
    formatted = {f"line{idx+1}": line.replace('\n', '') for idx, line in enumerate(lines)}
    with open(DOC_FILE, 'w') as f:
        json.dump(formatted, f, indent=2)
        
def maybe_save_document():
    global last_save_time
    now = time.time()
    if now - last_save_time > SAVE_INTERVAL:
        with write_lock:
            save_document(document_lines)
        last_save_time = now

def load_document():
    if os.path.exists(DOC_FILE):
        with open(DOC_FILE, 'r') as f:
            data = json.load(f)
            return [data[key] for key in sorted(data.keys(), key=lambda k: int(k.replace("line", "")))]
    return [""]

document_lines = load_document()
document_lines = [line if isinstance(line, str) else "" for line in document_lines]
history = []
client_revisions = {}
write_lock = Semaphore()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def connect():
    sid = request.sid
    client_revisions[sid] = len(history)
    emit('init', {
        'text': "\n".join(document_lines),
        'rev': len(history)
    })
    
@socketio.on('cursor')
def handle_cursor(data):
    data['sid'] = request.sid
    emit('cursor_update', data, broadcast=True, include_self=False)


@socketio.on('operation')
def handle_operation(data):
    global document_lines

    sid = request.sid
    base_rev = data['rev']
    op_type = data['type']
    line = data['line']
    col = data['col']
    char = data.get('char')

    # Rebuild operation object
    if op_type == 'insert':
        op = InsertOp(line, col, char)
    else:
        op = DeleteOp(line, col)

    # Transform against newer operations since client's last known revision
    for i in range(base_rev, len(history)):
        op = op.transform_against(history[i])
        if op is None:
            return

    # Apply operation
    document_lines = op.apply(document_lines)
    with write_lock:
        save_document(document_lines)
    history.append(op)
    client_revisions[sid] = len(history)

    emit('remote_op', {
        'type': op_type,
        'line': op.line,
        'col': op.col,
        'char': getattr(op, 'char', None),
        'rev': len(history)
    }, broadcast=True, include_self=False)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
