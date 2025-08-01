from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        raise ValueError("❌ DATABASE_URL not found or is empty!")

    print(f"✅ Loaded DATABASE_URL: {database_url}")

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.permanent_session_lifetime = timedelta(minutes=30)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # ⬇️ MOVE model import here after db is set up
    from ucolab.models import User  # Now it's safe

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from ucolab.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from ucolab.utils.socket_handlers import init_handlers
    init_handlers()

    return app
