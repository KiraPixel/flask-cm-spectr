import uuid

from flask import session, abort, jsonify, request
from flask_restx import Namespace, Resource
from ..utils import need_access, is_valid_api_key, get_api_key_by_username
from ..models import User, CashWialon, Alert, TransferTasks, db
from modules.my_time import one_hours_ago_unix, forty_eight_hours_ago_unix, now_unix_time

api_key_ns = Namespace('key', description='API key')


@api_key_ns.route('/generate-api-key')
class GenerateApiKey(Resource):
    @need_access(-1)
    def get(self):
        # Получаем данные пользователя из сессии
        user = session.get('username')
        if not user:
            abort(401, message="User not authenticated")

        def generate_unique_api_key():
            return str(uuid.uuid4())

        new_api_key = generate_unique_api_key()

        # Проверяем, существует ли уже такой API ключ
        while User.query.filter_by(api_token=new_api_key).first():
            new_api_key = generate_unique_api_key()  # Генерируем новый ключ, если такой уже существует

        user = User.query.filter_by(username=session['username']).first_or_404()

        user.api_token = new_api_key
        db.session.commit()

        return jsonify({'api_token': new_api_key})



@api_key_ns.route('/authorize-api-key')
class AuthorizeApiKey(Resource):
    @api_key_ns.doc(description='Авторизация по API-ключу. Передайте ключ в заголовке X-API-KEY.',
                    params={'X-API-KEY': {
                        'description': 'API-ключ для авторизации',
                        'in': 'header',
                        'type': 'string',
                        'required': True
                    }})
    def post(self):
        api_key = request.headers.get('X-API-KEY')

        if not api_key:
            abort(400, message="API key is required")

        # Проверка корректности ключа
        if is_valid_api_key(api_key):
            user = User.query.filter_by(api_token=api_key).first()
            session.permanent = True
            session['username'] = user.username
            return jsonify({'message': 'OK'})
        else:
            abort(401, message="Invalid API key")


@api_key_ns.route('/get-api-key')
class GetApiKey(Resource):
    @need_access(0)
    def get(self):
        # Получаем username из сессии
        username = session.get('username')

        if not username:
            abort(401, message="User not authenticated")

        # Получаем API ключ пользователя
        api_key = get_api_key_by_username(username)

        if api_key:
            return jsonify({'api_token': api_key})
        else:
            abort(404, message="API key not found for user")