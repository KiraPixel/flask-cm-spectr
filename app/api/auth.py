import jwt
import datetime
from functools import wraps

from flask import session, abort, jsonify, request, g, flash, redirect, url_for
from flask_restx import Namespace, Resource, fields

from modules import hash_password
from modules.my_time import now_unix_time
from ..config import SECRET_KEY
from ..utils import need_access, is_valid_api_key, get_api_key_by_username
from ..models import User, db


auth_ns = Namespace('jwt', description='JWT авторизация')


@auth_ns.route('/login')
class JwtLogin(Resource):
    @auth_ns.expect(
        auth_ns.model('LoginInput', {
            'username': fields.String(required=True, example='admin'),
            'password': fields.String(required=True, example='admin')
        })
    )
    def post(self):
        data = request.get_json()
        if not data:
            return {'message': 'JSON data required"', 'success': False}, 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'message': 'Username and password are required"', 'success': False}, 400

        user = User.query.filter_by(username=username).first()

        if user is None or not hash_password.compare_passwords(user.password, password):
            return {'message': 'Invalid username or password"', 'success': False}, 401

        # Генерация JWT с expiration 24 часа
        expiration = now_unix_time() + 86400

        token = jwt.encode({
            'user_id': user.id,
            'username': user.username,
            'exp': expiration,
            'iat': now_unix_time()
        }, SECRET_KEY, algorithm='HS256')

        message = {
            'token': token,
            'username': user.username,
            'user_id': user.id
        }
        return {'message': message,'success': True}, 200