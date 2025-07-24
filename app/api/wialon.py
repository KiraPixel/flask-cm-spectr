
import os

from flask import jsonify, request, session
from flask_restx import Namespace, Resource


from app.utils import need_access
from custom_api.wialon import WialonAPI

wialon_ns = Namespace('wialon', description='Wialon commands API')
wialon_token = os.getenv('WIALON_TOKEN', 'default_token')
wialon_api_url = os.getenv('WIALON_HOST', 'default_host')

# Создаем экземпляр WialonAPI
wialon_api = WialonAPI(wialon_token, wialon_api_url)

@wialon_ns.route('/wialon_exec_cmd/<int:unit_id>/<string:command_name>', methods=['GET'])
class WialonExecCmd(Resource):
    @wialon_ns.doc(params={
        'unit_id': 'Номер объекта в виалоне',
        'command_name': 'Имя команды'
    })
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access('car_command')
    def get(self, unit_id, command_name):
        """Выполнение команды на устройстве через Wialon"""
        username = session.get('username')

        response_data, status_code = wialon_api.execute_command(username, unit_id,command_name)

        if status_code == 200:
            if response_data:  # Проверка на пустой ответ
                return jsonify(response_data)
            return jsonify({'status': 'OK'})  # Возвращаем статус OK для пустого ответа
        else:
            return jsonify({'error': 'An error occurred', 'status_code': status_code,
                            'message': response_data}), status_code


@wialon_ns.route('/wialon_get_sensor/<int:unit_id>/')
class WialonGetSensor(Resource):
    @wialon_ns.doc(params={'unit_id': 'Номер объекта в виалоне'})
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access('car_sensors')
    def get(self, unit_id):
        username = session.get('username')

        final_response = wialon_api.fetch_sensor_data(username, unit_id)
        if final_response is not None:
            return jsonify(final_response)
        # После 6 неудачных попыток возвращаем ошибку
        return jsonify({'error': 'Failed to fetch valid sensor data after multiple attempts'}), 500


@wialon_ns.route('/wialon_get_unit_messages/')
class WialonGetUnitMessages(Resource):
    @wialon_ns.param('unit_id', 'Номер объекта в виалоне', type=int)
    @wialon_ns.param('time_to', 'unix time', type=int)
    @wialon_ns.param('time_from', 'unix time', type=int)
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access('car_sensors')
    def get(self):
        username = session.get('username')
        params = {
            'unit_id': request.args.get('unit_id', type=int),
            'time_from': request.args.get('time_from', type=int),
            'time_to': request.args.get('time_to', type=int)
        }
        if not all(params.values()):
            return jsonify({'error': 'Missing required parameters'}), 400

        final_response = wialon_api.get_unit_messages(username, params["unit_id"], params["time_from"], params["time_to"])
        if final_response is not None:
            return jsonify(final_response)
        return jsonify({'error': 'Failed to fetch unit messages after multiple attempts'}), 500


@wialon_ns.route('/wialon_get_unit_sensor_messages/')
class WialonGetUnitSensorMessages(Resource):
    @wialon_ns.param('unit_id', 'Номер объекта в виалоне', type=int)
    @wialon_ns.param('time_to', 'unix time', type=int)
    @wialon_ns.param('time_from', 'unix time', type=int)
    @wialon_ns.response(200, 'Успешно')
    @wialon_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @wialon_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access('car_sensors')
    def get(self):
        username = session.get('username')
        params = {
            'unit_id': request.args.get('unit_id', type=int),
            'time_from': request.args.get('time_from', type=int),
            'time_to': request.args.get('time_to', type=int)
        }
        if not all(params.values()):
            return jsonify({'error': 'Missing required parameters'}), 400

        final_response = wialon_api.get_unit_sensor_messages(username, params["unit_id"], params["time_from"], params["time_to"])
        if final_response is not None:
            return jsonify(final_response)
        return jsonify({'error': 'Failed to fetch unit sensor messages after multiple attempts'}), 500