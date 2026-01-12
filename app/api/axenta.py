import logging
from datetime import datetime
from flask import jsonify, request, g
from flask_restx import Namespace, Resource, fields
from app.utils import need_access
from app.utils.db_log import add_log
from app.utils.transport_acccess import check_access_to_transport
from app.models import CashAxenta
from custom_api.axenta import AxentaApi
import os

axenta_ns = Namespace('axenta', description='Axenta Cloud API')

axenta_api = AxentaApi(
    login=os.getenv('AXENTA_USERNAME'),
    password=os.getenv('AXENTA_PASSWORD'),
    api_url=os.getenv('AXENTA_HOST', 'https://axenta.cloud/api/')
)

logger = logging.getLogger('flask_cm_spectr')

coord_model = axenta_ns.model('Coordinate', {
    'lat': fields.Float(required=True, description='Широта', example=55.751244),
    'lng': fields.Float(required=True, description='Долгота', example=37.618423),
})

coords_array_model = axenta_ns.model('CoordinatesArray', {
    'coordinates': fields.List(
        fields.Nested(coord_model),
    )
})


@axenta_ns.route('/axenta_exec_cmd/<string:object_id>/<path:command_params>')
class AxentaExecCmd(Resource):
    @need_access('car_command')
    def get(self, object_id: str, command_params: str):
        username = g.user.username
        cash = CashAxenta.query.filter_by(id=object_id).first()
        if not cash or not check_access_to_transport(username, cash.nm):
            return jsonify({'status': 'not accessed'}), 403

        add_log(cash.nm, username, 'axenta', f'Command: {command_params}')
        success = axenta_api.send_command(object_id, command_params)
        return jsonify({'status': 'sent', 'command': command_params}) if success else (jsonify({'error': 'command failed'}), 500)


@axenta_ns.route('/axenta_get_sensors/<string:object_id>')
class AxentaGetSensors(Resource):
    @need_access('car_sensors')
    def get(self, object_id: str):
        data = axenta_api.get_sensors(object_id)
        return jsonify(data) if data is not None else (jsonify({'error': 'failed to get sensors'}), 500)


@axenta_ns.route('/axenta_get_commands/<string:object_id>')
class AxentaGetCommands(Resource):
    @need_access('car_sensors')
    def get(self, object_id: str):
        return jsonify(axenta_api.get_commands(object_id) or [])


@axenta_ns.route('/axenta_build_track/')
class AxentaBuildTrack(Resource):
    @axenta_ns.param('object_id', 'ID объекта в Axenta', required=True)
    @axenta_ns.param('start', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('end', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('detect_trips', 'true/false', default='true')
    @need_access('car_sensors')
    def get(self):
        object_id = request.args.get('object_id')
        start_ts = request.args.get('start', type=int)
        end_ts = request.args.get('end', type=int)
        detect_trips = request.args.get('detect_trips', 'true').lower() == 'true'

        if not all([object_id, start_ts, end_ts]):
            return jsonify({'error': 'missing or invalid params'}), 400

        track = axenta_api.build_track(
            object_id=object_id,
            start_ts=start_ts,
            end_ts=end_ts,
            detect_trips=detect_trips
        )
        return jsonify(track) if track is not None else (jsonify({'error': 'track build failed'}), 500)


@axenta_ns.route('/axenta_get_sensors_by_period/')
class AxentaGetSensorsByPeriod(Resource):
    @axenta_ns.param('object_id', 'ID объекта в Axenta', type=int, required=True)
    @axenta_ns.param('start', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('end', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('sensors', 'Список ID сенсоров, разделенных запятыми (например: 1733350,1733351)', required=True)
    @need_access('car_sensors')
    def get(self):
        object_id = request.args.get('object_id', type=int)
        start_ts = request.args.get('start', type=int)
        end_ts = request.args.get('end', type=int)
        sensors_str = request.args.get('sensors')

        if not all([object_id, start_ts, end_ts, sensors_str]):
            return {"error": "object_id, start, end, sensors — обязательны"}, 400

        try:
            sensor_ids = [int(sid.strip()) for sid in sensors_str.split(',') if sid.strip()]
            if not sensor_ids:
                raise ValueError
        except ValueError:
            return {"error": "sensors должен быть списком целых чисел, разделенных запятыми"}, 400

        data = axenta_api.get_sensors_by_period(
            object_id=object_id,
            start_ts=start_ts,
            end_ts=end_ts,
            sensor_ids=sensor_ids
        )
        if data is None:
            logger.error(f"Axenta: нет данных сенсоров за период | User: {g.user.username} | Obj: {object_id} | {start_ts}→{end_ts} | Sensors: {sensors_str}")
            return {"error": "Нет данных или ошибка Axenta"}, 500

        return data, 200


@axenta_ns.route('/axenta_reverse_geocode/', methods=['POST'])
class AxentaReverseGeocode(Resource):
    @axenta_ns.doc(
        description="""
        <strong>Axenta • Обратное геокодирование</strong><br><br>
        Одна точка → полный адрес | Массив → пакетный ответ<br><br>
        <pre>
        {
            "lat": 55.7558,
            "lng": 37.6173
        }
        </pre>
        или
        <pre>
        [
            {"lat": 55.7558, "lng": 37.6173},
            {"lat": 59.9311, "lng": 30.3609}
        ]
        </pre>
        """
    )
    @axenta_ns.expect(coord_model, validate=False)
    @need_access('car_sensors')
    def post(self):
        data = request.get_json(force=True, silent=True)
        if not data:
            return {"error": "Invalid JSON"}, 400

        if isinstance(data, dict) and "lat" in data and "lng" in data:
            coordinates = [data]
            is_single = True
        elif isinstance(data, list) and data:
            coordinates = data
            is_single = len(data) == 1
        else:
            return {"error": "Expected single point {lat,lng} or array of points"}, 400

        validated = []
        for i, point in enumerate(coordinates):
            try:
                lat = float(point["lat"])
                lng = float(point["lng"])
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    return {"error": f"Coordinate out of range at index {i}"}, 400
                validated.append({"lat": lat, "lng": lng})
            except (KeyError, TypeError, ValueError):
                return {"error": f"Invalid point at index {i}"}, 400

        result = axenta_api.reverse_geocode(validated)
        if result is None:
            logger.error(f"Axenta reverse_geocode failed | User: {g.user.username} | Count: {len(validated)}")
            return {"error": "Axenta service unavailable"}, 500

        if is_single:
            key = f"{validated[0]['lng']}_{validated[0]['lat']}"
            addr = result.get(key, {}).get("address", "")
            return {"lat": validated[0]["lat"], "lng": validated[0]["lng"], "address": addr}

        return result, 200


@axenta_ns.route('/axenta_get_sensor_messages/')
class AxentaGetSensorMessages(Resource):
    @axenta_ns.param('object_id', 'ID объекта в Axenta', type=int, required=True)
    @axenta_ns.param('start', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('end', 'Unix timestamp (секунды)', required=True)
    @axenta_ns.param('sort', 'asc/desc', default='desc')
    @axenta_ns.param('mode', 'sensors/raw', default='sensors')
    @need_access('car_sensors')
    def get(self):
        object_id = request.args.get('object_id', type=int)
        start_ts = request.args.get('start', type=int)
        end_ts = request.args.get('end', type=int)
        sort = request.args.get('sort', 'desc').lower()
        mode = request.args.get('mode', 'sensors')

        if not all([object_id, start_ts, end_ts]):
            return {"error": "object_id, start, end — обязательны и должны быть валидными unix-ts"}, 400

        if sort not in ('asc', 'desc'):
            sort = 'desc'
        if mode not in ('sensors', 'raw'):
            mode = 'sensors'

        data = axenta_api.get_messages_with_sensors(
            object_id=object_id,
            start_ts=start_ts,
            end_ts=end_ts,
            sort=sort,
            messages_param=mode
        )
        if data is None:
            logger.error(f"Axenta: нет сообщений | User: {g.user.username} | Obj: {object_id} | {start_ts}→{end_ts}")
            return {"error": "Нет данных или ошибка Axenta"}, 500

        return data, 200