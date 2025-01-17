import json
import os
import re
import time
import uuid

import bleach
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import warnings
from flask import Blueprint, request, jsonify, session, send_from_directory, abort
from flask_restx import Api, Resource, fields, Namespace
from . import db
from .utils import need_access, need_access, get_api_key_by_username, is_valid_api_key
from .models import Transport, TransportModel, Storage, User, CashWialon, Comments, Alert, CashHistoryWialon, Reports, \
    CashCesar, ParserTasks, TransferTasks
import modules.my_time as mytime

# Создаем Blueprint для API маршрутов приложения
api_bp = Blueprint('api', __name__)
api = Api(api_bp,
          version='1.0',
          title='API Documentation',
          description='Описание и документация для API',
          authorizations={
              'api_key': {
                  'type': 'apiKey',
                  'in': 'header',
                  'name': 'X-API-KEY'
              }
          },
          security='api_key'  # Эта строка указывает, что API ключ нужен для всех маршрутов
         )
wialon_api_namespace = Namespace('wialon', description='Wialon commands API')
api.add_namespace(wialon_api_namespace)
parser_api_namespace = Namespace('parser', description='Parser commands API')
api.add_namespace(parser_api_namespace)
api_key_namespace = Namespace('key', description='API key')
api.add_namespace(api_key_namespace)
wialon_token = os.getenv('WIALON_TOKEN', 'default_token')
wialon_api_url = os.getenv('WIALON_HOST', 'default_host')
warnings.simplefilter('ignore', InsecureRequestWarning)




@need_access(-1)
@api.route('/health')
class HealthCheck(Resource):
    def get(self):
        """Проверка состояния системы"""
        try:
            db.session.query(User).first()
            status_db = 1
            db_error = None
        except Exception as e:
            print(e)
            status_db = 0
            db_error = str(e)

        try:
            last_wialon_entry = CashWialon.query.order_by(CashWialon.last_time.desc()).first()
            if last_wialon_entry and last_wialon_entry.last_time >= mytime.one_hours_ago_unix():
                cashing_module = 1
                last_wialon_time = last_wialon_entry.last_time
            else:
                cashing_module = 0
                last_wialon_time = "No data"
        except Exception:
            cashing_module = 0
            last_wialon_time = "No data"

        try:
            last_alert_entry = Alert.query.order_by(Alert.date.desc()).first()
            if last_alert_entry and int(last_alert_entry.date) >= mytime.one_hours_ago_unix():
                voperator = 1
                last_alert_time = last_alert_entry.date
            else:
                voperator = 0
                last_alert_time = "No data"
        except Exception:
            voperator = 0
            last_alert_time = "No data"

        try:
            last_pars_entry = TransferTasks.query.order_by(TransferTasks.date.desc()).first()
            if last_pars_entry and int(last_pars_entry.date) >= mytime.forty_eight_hours_ago_unix():
                xml_parser = 1
                last_parser_time = last_pars_entry.date
            else:
                xml_parser = 0
                last_parser_time = "No data"
        except Exception:
            xml_parser = 0
            last_parser_time = "No data"

        return {
            'status_db': {
                'status': status_db,
                'error': db_error
            },
            'cashing_module': {
                'status': cashing_module,
                'last_time': last_wialon_time
            },
            'voperator_module': {
                'status': voperator,
                'last_time': last_alert_time
            },
            'xml_parser_module': {
                'status': xml_parser,
                'last_time': last_parser_time
            }
        }


@api.route('/cars')
class CarsResource(Resource):
    @api.param('type', 'Тип транспортного средства', type=str)
    @api.param('region', 'Регион', type=str)
    @api.response(200, 'Успешно')
    @api.response(404, 'Данные не найдены')
    @need_access(-1)
    def get(self):
        """Получение списка автомобилей с фильтрами"""
        filters = {
            'type': request.args.get('type', ''),
            'region': request.args.get('region', '')
        }

        user = User.query.filter_by(username=session['username']).first_or_404()

        user_access_managers = json.loads(user.access_managers)
        user_access_regions = json.loads(user.access_regions)

        query = db.session.query(Transport, Storage, TransportModel).join(
            Storage, Transport.storage_id == Storage.ID).join(
            TransportModel, Transport.model_id == TransportModel.id)

        if filters['type']:
            query = query.filter(TransportModel.type.like(f'%{filters["type"]}%'))
        if filters['region']:
            query = query.filter(Storage.region.like(f'%{filters["region"]}%'))

        if user.role <= -1:
            if user_access_managers:
                query = query.filter(Transport.manager.in_(user_access_managers))
            if user_access_regions:
                query = query.filter(Storage.region.in_(user_access_regions))

        data_db = query.all()

        if not data_db:
            return {'message': 'No data found.'}, 404

        wialon_cars = db.session.query(CashWialon).all()
        cesar_cars = db.session.query(CashCesar).all()

        result_dict = {}
        for transport in data_db:
            u_number = transport.Transport.uNumber or "Без ТС"
            result_dict[u_number] = {"uNumber": u_number, "devices": []}

        for wialon in wialon_cars:
            u_number = wialon.nm or "Без ТС"
            if u_number in result_dict:
                result_dict[u_number]["devices"].append({
                    "type": "Wialon",
                    "uNumber": wialon.nm,
                    "pos_x": wialon.pos_x,
                    "pos_y": wialon.pos_y,
                    "last_time": wialon.last_time
                })

        if user.cesar_access == 1:
            for cesar in cesar_cars:
                u_number = cesar.object_name or "Без ТС"
                if u_number in result_dict:
                    result_dict[u_number]["devices"].append({
                        "type": "Cesar",
                        "uNumber": cesar.object_name,
                        "pos_x": cesar.pos_y,
                        "pos_y": cesar.pos_x,
                        "last_time": cesar.last_time
                    })

        result_dict = {u_number: data for u_number, data in result_dict.items() if data["devices"]}
        result = list(result_dict.values())
        return jsonify(result)


@api.route('/get_car_history')
class GetCarHistory(Resource):

    @api.param('nm', 'Номер транспортного средства', _required=True)
    @api.param('time_from', 'Время начала фильтрации (UNIX timestamp)', _required=True)
    @api.param('time_to', 'Время окончания фильтрации (UNIX timestamp)', _required=True)
    @api.response(200, 'Успешно')  # Указываем модель для ответа
    @api.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @api.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(-1)
    def get(self):
        """Получение истории автомобиля по номеру и времени"""
        nm = request.args.get('nm')
        time_from = request.args.get('time_from')
        time_to = request.args.get('time_to')

        if not nm or not time_from or not time_to:
            return {'error': 'Missing required parameters: nm, time_from, time_to'}, 400

        try:
            time_from_unix = int(time_from)
            time_to_unix = int(time_to)
        except ValueError as e:
            return {'error': f'Invalid timestamp format: {str(e)}'}, 400

        try:
            # Выполняем запрос к базе данных
            history_entries = db.session.query(CashHistoryWialon).filter(
                CashHistoryWialon.nm == nm,
                CashHistoryWialon.last_time >= time_from_unix,
                CashHistoryWialon.last_time <= time_to_unix
            ).order_by(CashHistoryWialon.last_time.asc()).all()

            # Преобразуем объекты в словари
            result = [
                {
                    'uid': entry.uid,
                    'nm': entry.nm,
                    'pos_x': entry.pos_x,
                    'pos_y': entry.pos_y,
                    'last_time': entry.last_time
                }
                for entry in history_entries
            ]
            return result

        except Exception as e:
            print(f"Error occurred while fetching car history: {e}")
            return {'error': 'Database query failed'}, 500


@api.route('/change_disable_virtual_operator')
class ChangeDisableVirtualOperator(Resource):

    @api.param('car_name', 'Номер транспортного средства', _required=True)
    @api.response(200, 'Успешно обновлено')
    @api.response(400, 'Отсутствует параметр car_name')
    @api.response(404, 'Транспортное средство не найдено')
    @need_access(1)
    def get(self):
        """Изменение состояния disable_virtual_operator для транспортного средства"""
        car_name = request.args.get('car_name')

        if not car_name:
            return {'error': 'car_name is required'}, 400

        # Получаем транспортное средство по номеру
        transport = Transport.query.filter_by(uNumber=car_name).first()

        if not transport:
            return {'error': 'Transport not found'}, 404

        # Изменяем значение disable_virtual_operator
        transport.disable_virtual_operator = 1 - transport.disable_virtual_operator  # Меняем 0 на 1 и наоборот
        db.session.commit()

        return {'message': 'Successfully updated', 'new_state': transport.disable_virtual_operator}, 200



@api_key_namespace.route('/generate-api-key')
class GenerateApiKey(Resource):
    @need_access(-1)  # Проверка доступа
    def get(self):
        # Получаем данные пользователя из сессии
        user = session.get('username')  # Или используйте любой другой способ идентификации пользователя
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



@api_key_namespace.route('/authorize-api-key')
class AuthorizeApiKey(Resource):
    @need_access(-1)
    def post(self):
        # Получаем API ключ из запроса
        api_key = request.headers.get('X-API-KEY')

        if not api_key:
            abort(400, message="API key is required")

        # Проверка корректности ключа
        if is_valid_api_key(api_key):
            return jsonify({'message': 'OK'})
        else:
            abort(401, message="Invalid API key")


@api_key_namespace.route('/get-api-key')
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


@api_bp.route('/add_comment', methods=['POST'])
@need_access(-1)
def add_comment():
    text = request.form.get('text', '').strip()
    if not text:
        return jsonify({'status': 'comment_deny'})

    clean_text = bleach.clean(text, strip=True)
    if len(clean_text) > 500 or len(clean_text) <= 1:
        return jsonify({'status': 'comment_deny'})

    author = session.get('username')
    if not author:
        return jsonify({'status': 'comment_deny'})  # Можно также проверять авторизацию

    uNumber = request.form.get('uNumber')

    new_comment = Comments(author=author, text=clean_text, uNumber=uNumber, datetime_unix=mytime.now_unix_time())
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({'status': 'comment_ok'})


@api_bp.route('/edit_comment', methods=['POST'])
@need_access(-1)
def edit_comment():
    comment_id = request.form.get('comment_id')
    action = request.form.get('action')

    if not comment_id:
        return jsonify({'status': 'edit_deny'})

    author = session.get('username')
    if not author:
        return jsonify({'status': 'edit_deny'})  # Проверка авторизации

    # Находим комментарий по ID и проверяем, что автор совпадает
    comment = Comments.query.get(comment_id)
    if not comment or comment.author != author:
        return jsonify({'status': 'edit_deny'})

    # Если действие "удалить", обновляем uNumber
    if action == 'delete':
        comment.uNumber = f"{comment.uNumber}_removed"
        db.session.commit()
        return jsonify({'status': 'edit_ok'})

    # Для редактирования текста
    text = request.form.get('text', '').strip()
    if not text or len(text) > 500:
        return jsonify({'status': 'edit_deny'})

    comment.text = text
    db.session.commit()

    return jsonify({'status': 'edit_ok'})


@api_bp.route('/edit_report_comment', methods=['POST'])
@need_access(0)
def edit_report_comment():
    data = request.json
    report_id = data.get('comment_id')
    new_comment = data.get('comment')
    author = session.get('username')

    if not report_id or not author:
        return jsonify({'status': 'edit_deny'})

    report = Alert.query.get(report_id)

    # Для редактирования текста
    text = new_comment.strip()
    if not text or len(text) > 500:
        return jsonify({'status': 'edit_deny'})

    report.comment = text
    report.comment_editor = author
    report.date_time_edit = mytime.now_unix_time()
    db.session.commit()

    return jsonify({'status': 'edit_ok'})


def get_wialon_sid():
    params = {
        'token': wialon_token
    }
    response = requests.get(wialon_api_url, params={
        'svc': 'token/login',
        'params': json.dumps(params)
    }, verify=False)

    if response.status_code == 200:
        result = response.json()
        if 'eid' in result:
            return result['eid']
        else:
            return None
    else:
        return None


@wialon_api_namespace.route('/wialon_exec_cmd/<int:unit_id>/<string:command_name>', methods=['GET'])
class WialonExecCmd(Resource):

    @wialon_api_namespace.doc(params={
        'unit_id': 'Номер объекта в виалоне',
        'command_name': 'Имя команды'
    })
    @wialon_api_namespace.response(200, 'Успешно')
    @wialon_api_namespace.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_api_namespace.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(0)
    def get(self, unit_id, command_name):
        """Выполнение команды на устройстве через Wialon"""
        params = {
            'itemId': unit_id,
            'commandName': f"{command_name}",
            'linkType': '',
            'param': '',
            'timeout': 5,
            'flags': 0
        }
        response = requests.get(wialon_api_url, params={
            'svc': 'unit/exec_cmd',
            'params': json.dumps(params),
            'sid': get_wialon_sid()
        }, verify=False)

        if response.status_code == 200:
            final_response = response.json()
            if final_response:  # Проверка на пустой ответ
                return jsonify(final_response)
            return jsonify({'status': 'OK'})  # Возвращаем статус OK для пустого ответа
        else:
            return jsonify({'error': 'An error occurred', 'status_code': response.status_code,
                            'message': response.text}), response.status_code



def fetch_sensor_data(unit_id):
    params = {
        'unitId': unit_id,
        'sensors': '',
    }
    response = requests.get(wialon_api_url, params={
        'svc': 'unit/calc_last_message',
        'params': json.dumps(params),
        'sid': get_wialon_sid()
    }, verify=False)

    if response.status_code == 200:
        return response.json()
    else:
        return None


@wialon_api_namespace.route('/wialon_get_sensor/<int:unit_id>/')
class WialonGetSensor(Resource):

    @wialon_api_namespace.doc(params={'unit_id': 'Номер объекта в виалоне'})
    @wialon_api_namespace.response(200, 'Успешно')
    @wialon_api_namespace.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_api_namespace.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(0)
    def get(self, unit_id):
        max_retries = 4
        delay = 10

        for attempt in range(max_retries):
            final_response = fetch_sensor_data(unit_id)

            if final_response:
                # Проверяем, если любое из значений меньше -1
                if any(value < -1 for value in final_response.values()):
                    time.sleep(delay)
                else:
                    return jsonify(final_response)

            time.sleep(delay)

        # После 6 неудачных попыток возвращаем ошибку
        return jsonify({'error': 'Failed to fetch valid sensor data after multiple attempts'}), 500


add_new_car_model = parser_api_namespace.model('AddNewCarModel', {
    'uNumber': fields.String(required=True, description='Номер транспортного средства'),
    'modelId': fields.String(required=True, description='ID модели транспортного средства'),
    'storage_id': fields.Integer(required=True, description='ID склада'),
    'VIN': fields.String(required=True, description='VIN номер транспортного средства'),
    'year': fields.String(required=True, description='Код выпуска'),
    'customer': fields.String(description='Имя клиента'),
    'manager': fields.String(description='Менеджер, ответственный за транспорт'),
    'x': fields.Float(description='Координата x'),
    'y': fields.Float(description='Координата y'),
    'disable_virtual_operator': fields.Integer(required=True, description='Состояние виртуального оператора (0 или 1)'),
})


@parser_api_namespace.route('/add_new_car')
class AddNewCar(Resource):

    @parser_api_namespace.doc(description="Добавление нового автомобиля")
    @parser_api_namespace.expect(add_new_car_model)
    @parser_api_namespace.response(200, 'Успешно добавлено')
    @parser_api_namespace.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @parser_api_namespace.response(500, 'Ошибка при выполнении запроса к базе данных')
    def post(self):
        """Добавление нового автомобиля"""
        # Получаем данные из тела запроса
        data = request.json
        uNumber = data.get('uNumber')
        model_id = data.get('modelId')
        storage_id = data.get('storage_id')
        VIN = data.get('VIN')
        year = data.get('year')
        customer = data.get('customer')
        manager = data.get('manager')
        x = data.get('x')
        y = data.get('y')
        disable_virtual_operator = data.get('disable_virtual_operator')

        # Проверка, что disable_virtual_operator равен 0 или 1
        if disable_virtual_operator not in [0, 1]:
            return jsonify({'status': 'error', 'message': 'disable_virtual_operator должен быть 0 или 1'}), 400

        # Проверка уникальности uNumber
        if db.session.query(Transport).filter_by(uNumber=uNumber).first():
            return jsonify({'status': 'error', 'message': f'uNumber {uNumber} уже существует'}), 400

        # Проверка, что model_id существует в таблице transport_model
        if not db.session.query(TransportModel).filter_by(id=model_id).first():
            return jsonify({'status': 'error', 'message': f'Не найден transport_model с id {model_id}'}), 400

        # Проверка, что storage_id существует в таблице storage
        if not db.session.query(Storage).filter_by(ID=storage_id).first():
            return jsonify({'status': 'error', 'message': f'Не найден storage с ID {storage_id}'}), 400

        # Проверка длины VIN
        if not (4 <= len(VIN) <= 20):
            return jsonify({'status': 'error', 'message': 'VIN должен быть длиной от 4 до 20 символов'}), 400

        # Проверка типов для x и y (должны быть числа с плавающей точкой)
        try:
            x = float(x)
            y = float(y)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'x и y должны быть числами с плавающей точкой'}), 400

        # Теперь можно добавить запись в базу данных
        new_car = Transport(
            uNumber=uNumber,
            model_id=model_id,
            storage_id=storage_id,
            vin=VIN,
            customer=customer,
            manager=manager,
            manufacture_year=year,
            x=x,
            y=y,
            disable_virtual_operator=disable_virtual_operator
        )

        try:
            db.session.add(new_car)
            db.session.commit()

            # Теперь ищем соответствующую задачу и обновляем ее статус
            tasks = db.session.query(ParserTasks).filter(
                ParserTasks.task_name.in_(['new_car', 'new_car_error']),
                ParserTasks.variable == uNumber,
                ParserTasks.task_completed == 0
            ).all()

            for task in tasks:
                task.task_completed = 1

            if tasks:
                db.session.commit()

            return jsonify({'status': 'success', 'message': 'Машина добавлена и задача обновлена'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Ошибка добавления машины: {str(e)}'}), 500



@api_bp.route('/parser/close_task', methods=['POST'])
@need_access(1)
def close_task():
    data = request.json
    task_id = data.get('task_id')

    if not task_id:
        return jsonify({'error': 'task_id is required'}), 400

    # Ищем задачу по task_id с task_completed = 0
    task = db.session.query(ParserTasks).filter_by(id=task_id, task_completed=0).first()

    if not task:
        return jsonify({'error': f'Задача с id {task_id} не найдена или уже закрыта'}), 400

    # Обновляем статус задачи на 1 (закрыта)
    task.task_completed = 1

    try:
        db.session.commit()
        return jsonify({'status': 'task closed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при закрытии задачи: {str(e)}'}), 500
