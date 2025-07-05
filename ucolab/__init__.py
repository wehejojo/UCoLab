from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'data', 'app.db')

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Production (e.g., Railway PostgreSQL)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Development (local SQLite)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.permanent_session_lifetime = timedelta(minutes=30)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    from ucolab.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from ucolab.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from ucolab.utils.socket_handlers import init_handlers
    init_handlers()

    return app
