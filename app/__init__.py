from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
import json
import os

from custom_api.jira import jirasearcher
from .modules import MyTime

Jira = jirasearcher.JiraConnector(os.getenv('JIRA_URL', 'http://localhost:8080'), os.getenv('JIRA_USERNAME', 'default_bot_username'), os.getenv('JIRA_PASSWORD', 'default_bot_password'))
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

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    app.jinja_env.filters['unix_to_datetime'] = MyTime.unix_to_moscow_time
    app.jinja_env.filters['online_check'] = MyTime.online_check

    return app
