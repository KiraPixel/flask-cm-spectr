from flask import request, jsonify, session, json
from flask_restx import Namespace, Resource, fields
from ..utils import need_access, get_address_from_coords
from ..utils.transport_acccess import check_access_to_transport, get_all_access_transport, \
    validate_transport_access_rules, normalize_transport_access
from ..models import db, User, IgnoredStorage, Transport, Storage, SystemSettings
from modules import mail_sender, hash_password

admin_ns = Namespace('admin', description='Общие админские операции')
admin_users_ns = Namespace('admin/users', description='Операции с пользователями')
admin_storages_ns = Namespace('admin/storage', description='Операции со складами')

# Модель для пользователя
user_model = admin_users_ns.model('User', {
    'id': fields.Integer(description='Уникальный идентификатор пользователя'),
    'username': fields.String(description='Имя пользователя (логин)'),
    'email': fields.String(description='Электронная почта пользователя'),
    'role': fields.Integer(description='Роль пользователя: 0 (обычный пользователь), 1 (администратор)'),
    'cesar_access': fields.Integer(description='Доступ к системе Цезарь: 0 (нет доступа), 1 (есть доступ)'),
    'transport_access': fields.String(description='Фильтра для доступов к транспортам)'),
    'functionality_roles': fields.String(description='Функциональный роли')
}, description='Данные пользователя')

# Модель для склада
storage_model = admin_storages_ns.model('IgnoredStorage', {
    'id': fields.Integer(description='Уникальный идентификатор склада'),
    'named': fields.String(description='Название склада'),
    'pos_x': fields.Float(description='Широта (координата X)'),
    'pos_y': fields.Float(description='Долгота (координата Y)'),
    'radius': fields.Integer(description='Радиус зоны склада в километрах'),
    'address': fields.String(description='Адрес')
}, description='Данные о складе')

# Парсер для списка пользователей
user_parser = admin_users_ns.parser()
user_parser.add_argument('id', type=int, required=False, help='ID пользователя')

# Парсер для добавления пользователя
add_user_parser = admin_users_ns.parser()
add_user_parser.add_argument('username', type=str, required=True, help='Имя пользователя (логин, уникальное)', location='form')
add_user_parser.add_argument('email', type=str, required=True, help='Электронная почта пользователя (должна быть валидной)', location='form')

# Парсер для редактирования пользователя
edit_user_parser = admin_users_ns.parser()
edit_user_parser.add_argument('username', type=str, required=True, help='Имя пользователя (логин, уникальное)', location='form')
edit_user_parser.add_argument('email', type=str, required=True, help='Электронная почта пользователя (должна быть валидной)', location='form')
edit_user_parser.add_argument('role', type=int, required=True, help='Роль пользователя: -1 (обычный пользователь), 1 (администратор)', location='form')

# Парсер для добавления склада
storage_parser = admin_storages_ns.parser()
storage_parser.add_argument('name', type=str, required=True, help='Название склада (уникальное)', location='form')
storage_parser.add_argument('x_coord', type=str, required=True, help='Широта (координата X, например, 55.7558)', location='form')
storage_parser.add_argument('y_coord', type=str, required=True, help='Долгота (координата Y, например, 37.6173)', location='form')
storage_parser.add_argument('radius', type=int, required=True, help='Радиус зоны склада в километрах (целое число)', location='form')

# Парсер для установки transport_access
set_transport_access_parser = admin_users_ns.parser()
set_transport_access_parser.add_argument('transport_access', type=str, required=True, help='Правила доступа в формате JSON', location='json')

# Модель для возврата данных доступа
access_transport_data_model = admin_users_ns.model('AccessTransportData', {
    'uNumber': fields.List(fields.String, description='Список доступных uNumber'),
    'manager': fields.List(fields.String, description='Список доступных manager'),
    'region': fields.List(fields.String, description='Список доступных region'),
}, description='Данные доступа пользователя')

# Получение списка пользователей
@admin_users_ns.route('/')
class UsersList(Resource):
    @admin_users_ns.expect(user_parser)
    @admin_users_ns.marshal_with(user_model, as_list=True)
    @need_access(1)
    def get(self):
        """Получить список всех пользователей или одного, если передан ID"""
        args = user_parser.parse_args()
        user_id = args.get('id')

        if user_id is not None:
            user = User.query.filter_by(id=user_id).first()
            if user:
                return [user]
            else:
                admin_users_ns.abort(404, f"Пользователь с id={user_id} не найден")
        else:
            users = User.query.all()
            return users

# Добавление пользователя
@admin_users_ns.route('/add')
class AddUser(Resource):
    @admin_users_ns.expect(add_user_parser)
    @need_access(1)
    def post(self):
        """Добавить нового пользователя"""
        args = add_user_parser.parse_args()
        username = args['username']
        email = args['email']
        password = hash_password.generator_password()
        h_password = hash_password.hash_password(password)
        new_user = User(
            username=username,
            email=email,
            password=h_password,
            role=-1,
            last_activity="1999-12-02 00:00:00",
            transport_access='{"itn": [], "region": [], "manager": [], "uNumber": []}'
        )
        db.session.add(new_user)
        db.session.commit()
        mail_content = f'{new_user}|{password}'
        mail_sender.send_email(email, "Приглашение в Центр Мониторинга ЛК-СПЕКТР", mail_content, html_template='new_user')
        return {'status': 'user_added'}, 200

# Редактирование пользователя
@admin_users_ns.route('/edit/<int:user_id>')
class EditUser(Resource):
    @admin_users_ns.expect(edit_user_parser)
    @need_access(1)
    def put(self, user_id):
        """Редактировать данные пользователя"""
        args = edit_user_parser.parse_args()
        user = User.query.get_or_404(user_id)
        user.username = args['username']
        user.email = args['email']
        user.role = args['role']
        db.session.commit()
        return {'status': 'user_updated'}, 200

# Удаление пользователя
@admin_users_ns.route('/delete/<int:user_id>')
class DeleteUser(Resource):
    @need_access(1)
    def delete(self, user_id):
        """Удалить пользователя"""
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {'status': 'user_deleted'}, 200

# Установка доступа к системе Цезарь
@admin_users_ns.route('/set_cesar_access/<int:user_id>')
class SetCesarAccess(Resource):
    @need_access(1)
    def put(self, user_id):
        """Установить доступ пользователя к системе Цезарь (0 - нет доступа, 1 - есть доступ)"""
        access = request.args.get('access', type=int)
        if access not in [0, 1]:
            return {'status': 'error', 'message': 'Недопустимое значение для доступа (должно быть 0 или 1)'}, 400
        user = User.query.get_or_404(user_id)
        user.cesar_access = access
        db.session.commit()
        return {'status': 'cesar_access_updated'}, 200

@admin_users_ns.route('/get_transport_access_parameters')
class GetTransportAccessData(Resource):
    @admin_users_ns.marshal_with(access_transport_data_model)
    @need_access(1)
    def get(self):
        """Получить доступные для установки uNumber, manager и region"""
        default_storage = Storage.query.filter_by(ID=0).first()
        transports = Transport.query.all()
        regions = []
        for t in transports:
            storage = t.storage if t.storage else default_storage
            region = storage.region if storage else None
            if region:
                regions.append(region)
        return {
            'uNumber': list(set(t.uNumber for t in transports if t.uNumber)),
            'manager': list(set(t.manager for t in transports if t.manager)),
            'region': list(set(regions))
        }

# Назначение доступов пользователю
@admin_users_ns.route('/set_transport_access/<int:user_id>')
class SetTransportAccess(Resource):
    @admin_users_ns.expect(set_transport_access_parser)
    @need_access(1)
    def put(self, user_id):
        args = set_transport_access_parser.parse_args()
        user = User.query.get_or_404(user_id)
        is_valid, errors = validate_transport_access_rules(args['transport_access'])
        if not is_valid:
            return {'status': 'error', 'message': 'Неверные правила доступа', 'errors': errors}, 400
        # Используем ensure_ascii=False для сохранения кириллицы
        user.transport_access = json.dumps(normalize_transport_access(args['transport_access']), ensure_ascii=False)
        db.session.commit()
        return {'status': 'transport_access_updated'}, 200

# Сброс пароля
@admin_users_ns.route('/reset_pass/<int:user_id>')
class ResetPass(Resource):
    @need_access(1)
    def put(self, user_id):
        """Сбросить пароль пользователя и отправить новый по email"""
        user = User.query.get_or_404(user_id)
        new_password = hash_password.generator_password()
        user.password = hash_password.hash_password(new_password)
        db.session.commit()
        mail_sender.send_email(user.email, "Новый временный пароль для вашего аккаунта в ЛК-СПЕКТР", new_password, html_template='new_password')
        return {'status': 'password_reset'}, 200

# Получение списка складов
@admin_storages_ns.route('/')
class StoragesList(Resource):
    @admin_storages_ns.marshal_list_with(storage_model)
    @need_access(1)
    def get(self):
        """Получить список всех складов"""
        storages = IgnoredStorage.query.all()
        return storages

# Добавление склада
@admin_storages_ns.route('/add')
class AddStorage(Resource):
    @admin_storages_ns.expect(storage_parser)
    @need_access(1)
    def post(self):
        """Добавить новый склад"""
        args = storage_parser.parse_args()
        name = args['name']
        pos_x = float(args['x_coord'].replace(',', '.'))
        pos_y = float(args['y_coord'].replace(',', '.'))
        radius = args['radius']
        address = get_address_from_coords(pos_x, pos_y)
        new_storage = IgnoredStorage(named=name, pos_x=pos_x, pos_y=pos_y, radius=radius, address=address)
        db.session.add(new_storage)
        db.session.commit()
        return {'status': 'storage_added'}, 200

# Изменение склада
@admin_storages_ns.route('/edit/<int:storage_id>')
class EditStorage(Resource):
    @admin_storages_ns.expect(storage_parser)
    @need_access(1)
    def put(self, storage_id):
        """Обновить данные склада"""
        args = storage_parser.parse_args()
        storage = IgnoredStorage.query.get_or_404(storage_id)
        storage.named = args['name']
        storage.pos_x = float(args['x_coord'].replace(',', '.'))
        storage.pos_y = float(args['y_coord'].replace(',', '.'))
        storage.address = get_address_from_coords(storage.pos_x, storage.pos_y)
        storage.radius = args['radius']
        db.session.commit()
        return {'status': 'storage_updated'}, 200

# Удаление склада
@admin_storages_ns.route('/delete/<int:storage_id>')
class DeleteStorage(Resource):
    @need_access(1)
    def delete(self, storage_id):
        """Удалить склад по ID"""
        storage = IgnoredStorage.query.get_or_404(storage_id)
        db.session.delete(storage)
        db.session.commit()
        return {'status': 'storage_deleted'}, 200