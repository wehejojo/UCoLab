from functools import wraps
from flask import abort
from flask_login import current_user, login_required

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        print("ADMIN CHECK:", current_user.is_authenticated, current_user.is_admin)
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

