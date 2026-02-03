from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Zaloguj się, aby uzyskać dostęp.'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.servers import servers_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(reports_bp)

    with app.app_context():
        db.create_all()
        create_default_user()

    return app


def create_default_user():
    """Create default admin user if not exists."""
    from app.models import User
    user = User.query.filter_by(username='adminek').first()
    if not user:
        user = User(username='adminek')
        user.set_password('adminek123')
        db.session.add(user)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
