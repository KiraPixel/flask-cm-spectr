import os

SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

SQLALCHEMY_DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///default.db')

HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5000')

CESAR_USERNAME = os.getenv('CESAR_USERNAME', 'default_username')
CESAR_PASSWORD = os.getenv('CESAR_PASSWORD', 'default_password')

WIALON_TOKEN = os.getenv('WIALON_TOKEN', 'default_token')
