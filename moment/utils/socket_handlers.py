# import os, json
# BASE_DIR = os.path.dirname(__file__)
# DATA_FILE = os.path.join(BASE_DIR, "group_data.json")
# SAVE_INTERVAL = 0.5

# def get_group_file(group):
#     return os.path.join(BASE_DIR, f'document_{group}.json')

# def load_data():
#     if os.path.exists(DATA_FILE):
#         with open(DATA_FILE, "r") as f:
#             raw = json.load(f)
#             return defaultdict(lambda: {"text": "", "rev": 0}, raw)
#     return defaultdict(lambda: {"text": "", "rev": 0})

# def save_data():
#     try:
#         with open(DATA_FILE, "w") as f:
#             json.dump(dict(group_data), f, indent=2)
#         print(f"[Saved] group_data written to {DATA_FILE}")
#     except Exception as e:
#         print(f"[Error saving data]: {e}")

# def load_document(file_path):
#     if not os.path.exists(file_path):
#         return [""]
#     with open(file_path, 'r') as f:
#         data = json.load(f)
#     return [data[key] for key in sorted(data.keys(), key=lambda k: int(k.replace("line", "")))]


# def save_document(lines, file_path):
#     formatted = {f"line{idx+1}": line.replace('\n', '') for idx, line in enumerate(lines)}
#     with open(file_path, 'w') as f:
#         json.dump(formatted, f, indent=2)


# def load_group(group):
#     file_path = get_group_file(group)
#     documents[group] = [line if isinstance(line, str) else "" for line in load_document(file_path)]
#     histories[group] = []


from flask import request
from flask_socketio import emit
from eventlet.semaphore import Semaphore

from moment.utils.ot import InsertOp, DeleteOp
from moment import socketio, db
from moment.models import Group, Document

write_lock = Semaphore()

documents = {}
histories = {}
client_revisions = {}
client_groups = {}


def init_handlers():

    @socketio.on('connect')
    def handle_connect():
        sid = request.sid
        group_name = request.args.get('group')

        if not group_name:
            emit('error', {'message': 'Missing group parameter'})
            return

        group = Group.query.filter_by(name=group_name).first()
        if not group:
            group = Group(name=group_name)
            db.session.add(group)
            db.session.commit()

        doc = Document.query.filter_by(group_id=group.id).first()
        if not doc:
            doc = Document(group_id=group.id, text="", revision=0)
            db.session.add(doc)
            db.session.commit()

        lines = doc.text.split("\n") if doc.text else [""]
        documents[group_name] = lines
        histories[group_name] = []
        client_groups[sid] = group_name
        client_revisions[sid] = doc.revision

        emit('init', {
            'text': "\n".join(lines),
            'rev': doc.revision
        })

    @socketio.on('operation')
    def handle_operation(data):
        sid = request.sid
        group_name = client_groups.get(sid)

        if not group_name or group_name not in documents:
            return

        base_rev = data.get('rev', 0)
        op_type = data.get('type')
        line = data.get('line')
        col = data.get('col')
        char = data.get('char')

        op = InsertOp(line, col, char) if op_type == 'insert' else DeleteOp(line, col)

        for past_op in histories[group_name][base_rev:]:
            op = op.transform_against(past_op)
            if op is None:
                return

        documents[group_name] = op.apply(documents[group_name])
        histories[group_name].append(op)
        client_revisions[sid] = len(histories[group_name])

        with write_lock:
            group = Group.query.filter_by(name=group_name).first()
            doc = Document.query.filter_by(group_id=group.id).first()
            doc.text = "\n".join(documents[group_name])
            doc.revision = len(histories[group_name])
            db.session.commit()
 
        emit('remote_op', {
            'type': op_type,
            'line': op.line,
            'col': op.col,
            'char': getattr(op, 'char', None),
            'rev': doc.revision
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