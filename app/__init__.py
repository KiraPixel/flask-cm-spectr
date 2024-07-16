from .config import jira_config
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
import json
import os

from custom_api.jira import jirasearcher
from .modules import MyTime

Jira = jirasearcher.JiraConnector(jira_config['url'], jira_config['username'], jira_config['password'])
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    with open('config.json', 'r') as f:
        config = json.load(f)

    with open('config_jira.json', 'r') as f:
        jira_config = json.load(f)

    app.secret_key = config['SECRET_KEY']
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SQLALCHEMY_DATABASE_URI'] = config['SQLALCHEMY_DATABASE_URL']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"

    db.init_app(app)
    geolocator = Nominatim(user_agent="KiraPixel")

    from .routes import bp
    app.register_blueprint(bp)
    app.jinja_env.filters['unix_to_datetime'] = MyTime.unix_to_moscow_time


    return app