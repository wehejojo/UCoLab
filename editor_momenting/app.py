from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from ot import InsertOp, DeleteOp
from eventlet.semaphore import Semaphore
from collections import defaultdict

import os
import json


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')



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




# ------------- Main Entry --------------
group_data = load_data()
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
