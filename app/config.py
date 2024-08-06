import os

SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

SQLALCHEMY_DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///default.db')

HOST = os.getenv('HOST', '127.0.0.1')

CESAR_USERNAME = os.getenv('CESAR_USERNAME', 'default_username')
CESAR_PASSWORD = os.getenv('CESAR_PASSWORD', 'default_password')

WIALON_TOKEN = os.getenv('WIALON_TOKEN', 'default_token')

JIRA_USERNAME = os.getenv('JIRA_USERNAME', 'default_bot_username')
JIRA_PASSWORD = os.getenv('JIRA_PASSWORD', 'default_bot_password')
JIRA_URL = os.getenv('JIRA_URL', 'http://localhost:8080')
