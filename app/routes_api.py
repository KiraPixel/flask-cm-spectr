import json
import os
import time
import uuid

import bleach
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import warnings
from flask import Blueprint, request, jsonify, session, send_from_directory, abort

from . import db
from .utils import need_access, need_access
from .models import Transport, TransportModel, Storage, User, CashWialon, Comments, Alert
from .config import UPLOAD_FOLDER
import modules.my_time as mytime

# Создаем Blueprint для API маршрутов приложения
api_bp = Blueprint('api', __name__)
wialon_token = os.getenv('WIALON_TOKEN', 'default_token')
wialon_api_url = os.getenv('WIALON_HOST', 'default_host')
warnings.simplefilter('ignore', InsecureRequestWarning)


@need_access(-1)
@api_bp.route('/health', methods=['GET'])
def health_check():
    # Проверка состояния базы данных
    try:
        db.session.query(User).first()
        status_db = 1
        db_error = None
    except Exception as e:
        print(e)
        status_db = 0
        db_error = str(e)

    # Проверка cashing_module
    try:
        last_wialon_entry = CashWialon.query.order_by(CashWialon.last_time.desc()).first()
        if last_wialon_entry and last_wialon_entry.last_time >= mytime.one_hours_ago_unix():
            cashing_module = 1
            last_wialon_time = last_wialon_entry.last_time
        else:
            cashing_module = 0
            last_wialon_time = "No data"
    except Exception as e:
        cashing_module = 0
        last_wialon_time = "No data"

    # Проверка voperator_model
    try:
        last_alert_entry = Alert.query.order_by(Alert.date.desc()).first()
        if last_alert_entry and int(last_alert_entry.date) >= mytime.one_hours_ago_unix():
            voperator = 1
            last_alert_time = last_alert_entry.date
        else:
            voperator = 0
            last_alert_time = "No data"
    except Exception as e:
        voperator = 0
        last_alert_time = "No data"

    return jsonify({
        'status_db': {
            'status': status_db,
            'error': db_error
        },
        'cashing_module': {
            'status': cashing_module,
            'last_time': last_wialon_time
        },
        'voperator_model': {
            'status': voperator,
            'last_time': last_alert_time
        }
    }), 200


@api_bp.route('/cars', methods=['GET'])
@need_access(-1)
def get_cars():
    # Получаем данные из базы
    data_db = db.session.query(CashWialon).all()

    # Фильтруем транспорт по доступам пользователя
    user = User.query.filter_by(username=session['username']).first_or_404()
    if user.role <= -1:
        user_access = json.loads(user.access)
        data_db = [item for item in data_db if item[0].manager in user_access]

    # Преобразуем данные в JSON
    cars_json = [{
        "nm": car.nm,
        "pos_x": car.pos_x,
        "pos_y": car.pos_y,
        "last_time": car.last_time
    } for car in data_db]

    return jsonify(cars_json)


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

    new_comment = Comments(author=author, text=clean_text, uNumber=uNumber)
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({'status': 'comment_ok'})


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


@api_bp.route('/wialon_exec_cmd/<int:unit_id>/<string:command_name>', methods=['GET'])
@need_access(0)
def wialon_exec_cmd(unit_id, command_name):
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


@api_bp.route('/wialon_get_sensor/<int:unit_id>/', methods=['GET'])
@need_access(-1)
def wialon_get_sensor(unit_id):
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
