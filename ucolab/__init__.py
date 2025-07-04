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

    app.config['SECRET_KEY'] = 'your_secret_key_here'
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{db_path}")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
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

    from ucolab.models import User

    with app.app_context():
        try:
            admin = User.query.filter_by(name="admin").first()
            if not admin:
                admin_password = 'THE_UCOLAB_MOMENT'
                if not admin_password:
                    raise RuntimeError("ADMIN PASSWORD is not an environment variable")
                hashed_pass = bcrypt.generate_password_hash(admin_password)

                admin = User(
                    name='admin',
                    email='admin@ucolab',
                    password=hashed_pass,
                    is_admin=True
                )

                db.session.add(admin)
                db.session.commit()
                print("Admin created")
            else:
                print(f"Admin {admin.password} already exists")
        except Exception as e:
            print(f"Skipping admin creation during migration: {e}")


    return app
