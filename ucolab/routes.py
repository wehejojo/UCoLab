from flask import (
    Blueprint, abort, render_template, request, session,
    redirect, url_for, current_app, jsonify, flash
)
from flask_socketio import emit
from flask_bcrypt import Bcrypt

from flask_login import (
    login_user, login_required, 
    logout_user, current_user
)

from ucolab import socketio
from ucolab.matchUsers import run_matching_sqlalchemy

from ucolab.models import (
    db, User, Answer, Group, GroupMembership,
    RegisterForm, LoginForm
)

import string, random

main = Blueprint('main', __name__)
bcrypt = Bcrypt()

def generateRandomSessionCode(length: int) -> str:
    characters: str = string.ascii_letters.upper() + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_group_data_by_user_name(name):
    user = User.query.filter_by(name=name).first()
    if not user:
        return None

    group = (
        db.session.query(Group)
        .join(GroupMembership, Group.id == GroupMembership.group_id)
        .join(User, User.id == GroupMembership.user_id)
        .filter(User.name == name)
        .first()
    )

    if not group:
        return None

    group_users = (
        db.session.query(User)
        .join(GroupMembership)
        .filter(GroupMembership.group_id == group.id)
        .all()
    )

    members = []
    for u in group_users:
        answers_dict = {a.question_id: a.answer for a in u.answers}
        members.append({
            "name": u.name,
            "college": u.college,
            "skills": u.skills.split(",") if u.skills else [],
            "answers": answers_dict
        })

    return group.name, members

SESSION_CODE: str = generateRandomSessionCode(4)

@main.route('/', methods=['GET', 'POST'])
def index():
    session.clear()
    return render_template('LandingPage.html')

@main.route('/error')
def error():
    error_message = request.args.get('error_message', 'An unknown error occurred.')
    return render_template('error.html', error_message=error_message)

@main.route('/master/session', methods=['GET', 'POST'])
def masterSession():
    if not current_user.is_authenticated or not current_user.is_admin:
        return abort(403)
    if request.method == 'POST':
        return redirect(url_for('main.masterMatch'))
    return render_template('/admin/master_session.html', session_code=SESSION_CODE)

@main.route('/master/match', methods=['GET'])
def masterMatch():
    if not current_user.is_authenticated or not current_user.is_admin:
        return abort(403)
    
    users = User.query.all()
    participants = [{
        'name': user.name,
        'college': user.college,
        'skills': user.skills
    } for user in users]
    return render_template(
        '/admin/match.html', session_code=SESSION_CODE,
        participants=participants, length=len(participants)
    )

@main.route('/mode-select', methods=['GET', 'POST'])
def modeSelect():
    if request.method == 'POST':
        user_code = request.form.get('code')
        if not user_code:
            return render_template('error.html', error_message="Please enter a code.")  
        if user_code == SESSION_CODE:
            return redirect(url_for('main.sessionPage', session_code=SESSION_CODE))
        return redirect(url_for('main.error', error_message="Wrong Code!!"))
    return render_template('/client/mode_select.html')

@main.route('/session/<session_code>', methods=['GET', 'POST'])
def sessionPage(session_code):
    form = RegisterForm()
    form.submit.label.text = 'Lock In'

    if form.validate_on_submit():
        hashed_pass = bcrypt.generate_password_hash(form.password.data)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_pass,
            college=form.college.data,
            skills=form.skills.data
        )

        db.session.add(new_user)
        db.session.commit()

        # ✅ Emit to all clients
        users = User.query.all()
        participants = [{
            'name': user.name,
            'college': user.college,
            'skills': user.skills
        } for user in users]

        socketio.emit('update', {
            'participants': participants,
            'count': len(participants)
        })

        return redirect(url_for('main.sessionPage', session_code=session_code))

    users = User.query.all()
    participants = [{
        'name': user.name,
        'college': user.college,
        'skills': user.skills
    } for user in users]

    return render_template(
        '/client/match.html',
        session_code=session_code,
        participants=participants,
        length=len(participants),
        form=form
    )

@main.route('/master/quiz')
def masterQuiz():
    if not current_user.is_authenticated or not current_user.is_admin:
        return abort(403)
    
    return render_template('/admin/quiz.html', session_code=SESSION_CODE)

@main.route('/<session_code>/quiz')
def quiz(session_code):
    return render_template('/client/quiz.html', session_code=session_code)

@main.route('/quiz/submit', methods=['POST'])
def submitQuiz():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400

    data = request.get_json()
    name = data.get('name')
    question_id = data.get('question_id')
    answer = data.get('answer')

    if not question_id or not answer or not name:
        return jsonify({'success': False, 'error': 'Missing name, question_id, or answer'}), 400
    
    user = User.query.filter_by(name=name).first()
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    existing_answer = Answer.query.filter_by(
        user_id = user.id,
        question_id = question_id
    ).first()

    if existing_answer:
        existing_answer.answer = answer
    else:
        new_answer = Answer(user_id=user.id, question_id=question_id, answer=answer)
        db.session.add(new_answer)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Answer submitted successfully'})

@main.route('/match', methods=['POST'])
def match_users():
    users = User.query.all()
    complete_users = [u for u in users if len(u.answers) == 5]

    if not complete_users:
        return jsonify({'error': 'No users with complete answers found'}), 400

    groups_data = run_matching_sqlalchemy(complete_users)
    if not groups_data:
        return jsonify({'error': 'Unable to form any groups'}), 400

    GroupMembership.query.delete()
    Group.query.delete()
    db.session.commit()

    for group_name, group_info in groups_data.items():
        group = Group(name=group_name)
        group.users = group_info["user_objs"]
        db.session.add(group)

    db.session.commit()

    print(group_name)

    return jsonify({
        "success": True,
        "groups": {
            group_name: {
                "members": {
                    u.name: {
                        "skills": u.skills
                    } for u in group_info["user_objs"]
                }
            } for group_name, group_info in groups_data.items()
        }
    }), 200

@main.route('/quiz/group', methods=["GET"])
def render_group():
    return render_template('/client/groups.html', session_code=SESSION_CODE)

@main.route('/getGroups', methods=['GET'])
def get_groups():
    name = request.args.get("name")
    if not name:
        return jsonify({"success": False, "error": "Missing 'name' parameter"}), 400

    result = get_group_data_by_user_name(name)
    if not result:
        return jsonify({"success": False, "error": "User not found or not in a group"}), 404

    group_name, members = result

    return jsonify({
        "success": True,
        "groups": {
            group_name: {
                "members": {str(i + 1): member for i, member in enumerate(members)}
            }
        },
        "currentuser": name
    }), 200

@main.route('/group/<group_name>')
def view_group(group_name):
    name = request.args.get("name") 

    if not name:
        return redirect(url_for('main.error', error_message="Missing 'name' parameter"))

    result = get_group_data_by_user_name(name)
    if not result:
        return redirect(url_for('main.error', error_message="User not found or not in a group"))

    user_group_name, members = result

    print(f"{name}\n{user_group_name}\n{group_name}")

    if user_group_name != group_name:
        return redirect(url_for('error.html', error_message=f"User {name} is not in this group"))

    return render_template('client/view_group.html', group_name=group_name, members=members)

@main.route('/doc/<group_name>')
def generate_doc(group_name):
    group = Group.query.filter_by(name=group_name).first()
    if not group:
        return redirect(url_for('main.error', error_message="Group not found"))

    group_users = (
        db.session.query(User)
        .join(GroupMembership)
        .filter(GroupMembership.group_id == group.id)
        .all()
    )

    members = []
    for user in group_users:
        answers_dict = {a.question_id: a.answer for a in user.answers}
        members.append({
            "name": user.name,
            "college": user.college,
            "skills": user.skills.split(",") if user.skills else [],
            "answers": answers_dict
        })

    return render_template(
        'client/editor.html',
        group_name=group_name,
        members=members
    )

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pass = bcrypt.generate_password_hash(form.password.data)
        new_user = User(
            name = form.name.data,
            email = form.email.data,
            password = hashed_pass,
            college = form.college.data,
            skills = form.skills.data
        )
        
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('auth/register.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash("User not found!", "danger")
        elif not bcrypt.check_password_hash(user.password, form.password.data):
            flash("Invalid password!", "danger")
        else:
            login_user(user)
            return redirect(url_for('main.modeSelect'))

    return render_template('auth/login.html', form=form)

@main.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    print('logged out')
    return redirect(url_for('main.login'))

# -------------------- Socket.IO Events -------------------- #

@socketio.on('connect')
def handle_connect():
    users = User.query.all()
    participants = [{
        'name': user.name,
        'college': user.college,
        'skills': user.skills
    } for user in users]

    emit('update', {
        'participants': participants,
        'count': len(participants)
    })

@socketio.on('join')
def handle_join(data):    
    name = data.get('name')
    college = data.get('college')
    skills = data.get('skills')

    user = User.query.filter_by(name=name).first()
    if not user:
        user = User(name=name, college=college, skills=skills)
        db.session.add(user)
        db.session.commit()
    
    users = User.query.all()
    participants = [{'name': u.name, 'college': u.college, 'skills': u.skills} for u in users]

    emit('update', {
        'participants': participants,
        'count': len(participants)
    }, broadcast=True)

@socketio.on('start_matching')
def handle_start_matching(data):
    session_code = data.get('url').split('/')[1]
    with current_app.app_context():
        quiz_url = url_for('main.quiz', session_code=session_code)
    emit('redirect_to_quiz', {'url': quiz_url}, broadcast=True)
