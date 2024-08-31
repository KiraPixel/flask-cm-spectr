from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
import os

from modules import my_time


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///default.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"

    db.init_app(app)
    geolocator = Nominatim(user_agent="KiraPixel")

    from .routes import bp as main_bp
    from .routes_api import api_bp
    from .routes_admin import admin_bp
    from .routes_user_settings import us_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)
    app.register_blueprint(us_bp, url_prefix='/user_settings')

    app.jinja_env.filters['unix_to_datetime'] = my_time.unix_to_moscow_time
    app.jinja_env.filters['online_check'] = my_time.online_check

    return app
