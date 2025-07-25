import logging
from datetime import timedelta
from flask import Flask, session, g
import os

from .routes_sbi import sbi
from .utils import storage_id_to_name, get_alert_type, get_user_roles
from .models import db, User

from modules import my_time, location_module




def create_app():
    app = Flask(__name__)
    logger = logging.getLogger('flask_cm_spectr')

    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///default.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"
    db.init_app(app)

    from .routes import bp as main_bp
    from .api import api_bp
    from .routes_user_settings import us_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(us_bp, url_prefix='/user_profile')
    app.register_blueprint(sbi, url_prefix='/sbi')

    app.jinja_env.filters['unix_to_datetime'] = my_time.unix_to_moscow_time
    app.jinja_env.filters['online_check'] = my_time.online_check
    app.jinja_env.filters['get_address'] = location_module.get_address_decorator
    app.jinja_env.filters['storage_id_to_name'] = storage_id_to_name
    app.jinja_env.filters['get_alert_type'] = get_alert_type

    @app.before_request
    def set_current_user():
        g.user = None
        g.role = None

        try:
            if session is None:
                return
            if not 'username' is session:
                return
            username = session['username']
            if not username:
                return
            user = User.query.filter_by(username=username).first()
            if user is not None:
                g.user = user
                g.role = get_user_roles(g.user)
        except Exception as e:
            logger.debug(
                'Can not set user: ERROR=%s',
                e
            )

    return app
