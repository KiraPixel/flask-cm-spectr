from flask import request
from flask_restx import Namespace, Resource, fields
from ..utils import need_access, get_address_from_coords
from ..utils.functionality_acccess import validate_functionality_roles
from ..utils.transport_acccess import validate_transport_access_rules
from ..models import db, User, IgnoredStorage, Transport, Storage, FunctionalityAccess
from modules import mail_sender, hash_password
from ..utils.users import create_new_user

admin_ns = Namespace('admin', description='Общие админские операции')
admin_users_ns = Namespace('admin/users', description='Операции с пользователями')
admin_storages_ns = Namespace('admin/storage', description='Операции со складами')

# Модель для пользователя
user_model = admin_users_ns.model('User', {
    'id': fields.Integer(description='Уникальный идентификатор пользователя'),
    'username': fields.String(description='Имя пользователя (логин)'),
    'email': fields.String(description='Электронная почта пользователя'),
    'role': fields.Integer(description='Роль пользователя: 0 (обычный пользователь), 1 (администратор)'),
    'transport_access': fields.String(description='Фильтра для доступов к транспортам)'),
    'functionality_roles': fields.String(description='Функциональный роли'),
    'last_activity': fields.String(description='Последний вход пользователя')
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

# Модель для возврата данных доступа к тс
access_transport_data_model = admin_users_ns.model('AccessTransportData', {
    'uNumber': fields.List(fields.String, description='Список доступных uNumber'),
    'manager': fields.List(fields.String, description='Список доступных manager'),
    'region': fields.List(fields.String, description='Список доступных region'),
}, description='Данные доступа пользователя')


# Парсер для входных данных
set_functionality_roles_parser = admin_users_ns.parser()
set_functionality_roles_model = admin_users_ns.model('SetFunctionalityRoles', {
    'functionality_roles': fields.List(
        fields.Integer,
        required=False,
        description='Список идентификаторов ролей функциональности (может быть null или пустым)',
        nullable=True
    )
})

# Модель для возврата данных доступа к функционалу
access_functionality_data_model = admin_users_ns.model('FunctionalityAccess', {
    'id': fields.Integer(readonly=True, description='Уникальный идентификатор доступа к функциональности'),
    'name': fields.String(required=True, description='Название функциональности'),
    'localization': fields.String(required=True, description='Локализация функциональности'),
    'category': fields.String(required=True, description='Категория функциональности'),
    'category_localization': fields.String(required=True, description='Локализация категории')
})


# Получение списка пользователей
@admin_users_ns.route('/')
class UsersList(Resource):
    @admin_users_ns.expect(user_parser)
    @admin_users_ns.marshal_with(user_model, as_list=True)
    @need_access('admin_panel')
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
    @need_access('admin_panel')
    def post(self):
        """Добавить нового пользователя"""
        args = add_user_parser.parse_args()
        username = args['username']
        email = args['email']
        password = hash_password.generator_password()
        h_password = hash_password.hash_password(password)

        cnu = create_new_user(email, username, h_password)
        if cnu:
            mail_content = f'{username}|{password}'
            mail_sender.send_email(email, "Приглашение в Центр Мониторинга ЛК-СПЕКТР", mail_content, html_template='new_user')
            return {'status': 'user_added'}, 200
        else:
            return {'status': 'user_not_created'}, 404

# Редактирование пользователя
@admin_users_ns.route('/edit/<int:user_id>')
class EditUser(Resource):
    @admin_users_ns.expect(edit_user_parser)
    @need_access('admin_panel')
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
    @need_access('admin_panel')
    def delete(self, user_id):
        """Удалить пользователя"""
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {'status': 'user_deleted'}, 200


@admin_users_ns.route('/get_transport_access_parameters')
class GetTransportAccessData(Resource):
    @admin_users_ns.marshal_with(access_transport_data_model)
    @need_access('admin_panel')
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


@admin_users_ns.route('/set_transport_access/<int:user_id>')
class SetTransportAccess(Resource):
    @admin_users_ns.expect(set_transport_access_parser)
    @need_access('admin_panel')
    def put(self, user_id):
        """Установить uNumber, manager и region для пользователя"""
        args = set_transport_access_parser.parse_args()
        transport_access = args['transport_access']
        is_valid, errors = validate_transport_access_rules(transport_access)
        if not is_valid:
            return {'status': 'error', 'message': 'Неверные правила доступа', 'errors': errors}, 400
        user = User.query.get_or_404(user_id)
        user.transport_access = transport_access
        db.session.commit()
        return {'status': 'transport_access_updated'}, 200


@admin_users_ns.route('/get_functionality_access_parameters')
class GetFunctionalityAccessData(Resource):
    @admin_users_ns.marshal_with(access_functionality_data_model)
    @need_access('admin_panel')
    def get(self):
        """Получить доступные для установки uNumber, manager и region"""
        functionality = FunctionalityAccess.query.all()
        return functionality


@admin_users_ns.route('/set_functionality_roles/<int:user_id>')
class SetFunctionalityRoles(Resource):
    @admin_users_ns.expect(set_functionality_roles_model)
    @need_access('admin_panel')
    def put(self, user_id):
        """Установить роли функциональности для пользователя"""
        data = request.get_json()
        functionality_roles = data.get('functionality_roles')

        is_valid, errors, validated_roles = validate_functionality_roles(functionality_roles)
        if not is_valid:
            return {'status': 'error', 'message': 'Неверные роли функциональности', 'errors': errors}, 400

        user = User.query.get_or_404(user_id)
        user.functionality_roles = validated_roles
        db.session.commit()

        return {'status': 'functionality_roles_updated'}, 200


# Сброс пароля
@admin_users_ns.route('/reset_pass/<int:user_id>')
class ResetPass(Resource):
    @need_access('admin_panel')
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
    @need_access('admin_panel')
    def get(self):
        """Получить список всех складов"""
        storages = IgnoredStorage.query.all()
        return storages

# Добавление склада
@admin_storages_ns.route('/add')
class AddStorage(Resource):
    @admin_storages_ns.expect(storage_parser)
    @need_access('admin_panel')
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
    @need_access('admin_panel')
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
    @need_access('admin_panel')
    def delete(self, storage_id):
        """Удалить склад по ID"""
        storage = IgnoredStorage.query.get_or_404(storage_id)
        db.session.delete(storage)
        db.session.commit()
        return {'status': 'storage_deleted'}, 200