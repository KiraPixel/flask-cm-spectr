import json
import os
import time

import requests
from flask import jsonify, request
from flask_restx import Namespace, Resource
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import warnings

from app.utils import need_access
from custom_api.api_wialon_connector import get_message_for_interval

wialon_ns = Namespace('wialon', description='Wialon commands API')

wialon_token = os.getenv('WIALON_TOKEN', 'default_token')
wialon_api_url = os.getenv('WIALON_HOST', 'default_host')
warnings.simplefilter('ignore', InsecureRequestWarning)

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

@wialon_ns.route('/wialon_exec_cmd/<int:unit_id>/<string:command_name>', methods=['GET'])
class WialonExecCmd(Resource):
    @wialon_ns.doc(params={
        'unit_id': 'Номер объекта в виалоне',
        'command_name': 'Имя команды'
    })
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
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


@wialon_ns.route('/wialon_get_sensor/<int:unit_id>/')
class WialonGetSensor(Resource):

    @wialon_ns.doc(params={'unit_id': 'Номер объекта в виалоне'})
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(-1)
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


@wialon_ns.route('/wialon_get_unit_message/')
class WialonGetUnitMessages(Resource):
    @wialon_ns.param('unit_id', 'Номер объекта в виалоне', type=int)
    @wialon_ns.param('time_to', 'unix time', type=int)
    @wialon_ns.param('time_from', 'unix time', type=int)
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(0)
    def get(self):
        params = {
            'unit_id': request.args.get('unit_id', ''),
            'time_from': request.args.get('time_from', ''),
            'time_to': request.args.get('time_to', '')
        }
        final_response = get_message_for_interval(params["unit_id"], params["time_from"], params["time_to"])
        if final_response:
            return jsonify(final_response)
        else:
            return jsonify({'error': 'Failed to fetch valid sensor data after multiple attempts'}), 500


@wialon_ns.route('/wialon_get_unit_sensor_messages/')
class WialonGetUnitSensorMessages(Resource):
    @wialon_ns.param('unit_id', 'Номер объекта в виалоне', type=int)
    @wialon_ns.param('time_to', 'unix time', type=int)
    @wialon_ns.param('time_from', 'unix time', type=int)
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(-1)
    def get(self):
        params = {
            'unit_id': request.args.get('unit_id', ''),
            'time_from': request.args.get('time_from', ''),
            'time_to': request.args.get('time_to', '')
        }
        final_response = get_message_for_interval(params["unit_id"], params["time_from"], params["time_to"])
        if not final_response:
            return jsonify({'error': 'Failed to fetch valid sensor data after multiple attempts'}), 500

        formatted_response = []
        try:
            for message in final_response:
                message_time = message.get('t', 0)
                sensors = message.get('sensors', '')

                formatted_response.append({
                    'message_time': message_time,
                    'sensors': sensors
                })
        except Exception as e:
            print(e)

        return jsonify(formatted_response)