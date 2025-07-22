from flask import session, jsonify, request
from flask_restx import Namespace, Resource
from ..utils import need_access, get_address_from_coords, storage_id_to_name
from ..models import User, CashWialon, Alert, TransferTasks, db, Transport, Storage, TransportModel, CashCesar, \
    AlertType, Comments, CashHistoryWialon, AlertTypePresets, CashHistoryCesar
from modules.my_time import unix_to_moscow_time, online_check_cesar, online_check
from ..utils.functionality_acccess import has_role_access

from ..utils.transport_acccess import check_access_to_transport, get_all_access_transport

car_ns = Namespace('car', description='Car info')

@car_ns.route('/get_info/<lot_number>')
class GetCarInfo(Resource):
    @car_ns.doc(params={
        'lot_number': 'Номер лота'
    })
    @car_ns.response(200, 'Успешно')
    @car_ns.response(404, 'Лот не был найден')
    @need_access(-1)
    def get(self, lot_number):
        try:
            user = User.query.filter_by(username=session['username']).first_or_404()
            car = db.session.query(Transport).filter(Transport.uNumber == lot_number).first()
            if not car:
                return "Car not found", 404

            # Получение информации о хранилище
            storage = db.session.query(Storage).filter(Storage.ID == car.storage_id).first()
            if not storage:
                return {"error": "Storage not found for the specified car"}, 404

            # Получение информации о модели
            transport_model = db.session.query(TransportModel).filter(TransportModel.id == car.model_id).first()
            if not transport_model:
                return {"error": "Transport model not found for the specified car"}, 404

            if not check_access_to_transport(user.username, car.uNumber):
                return {"error": "You don't have access to this car"}, 403

            # Получение информации из Wialon
            wialon = db.session.query(CashWialon).filter(CashWialon.nm.like(car.uNumber)).all()
            monitoring_json_response = {"monitoring": []}
            if wialon:
                for item in wialon:
                    monitoring_json_block = {
                        "type": 'wialon',
                        "online": online_check(item.last_time),
                        "uid": item.uid,
                        "unit_id": item.id,
                        "pos_x": item.pos_y,
                        "pos_y": item.pos_x,
                        "address": str(get_address_from_coords(item.pos_y, item.pos_x)),
                        "last_time": unix_to_moscow_time(item.last_time),
                        "wialon_cmd": item.cmd,
                        "wialon_sensors_list": item.sens,
                        "wialon_satellite_count": item.gps,
                    }
                    monitoring_json_response["monitoring"].append(monitoring_json_block)

            # Получение информации из Cesar Position
            if has_role_access(user.username, 'csp'):
                cesar = db.session.query(CashCesar).filter(CashCesar.object_name.like(car.uNumber)).all()
                for item in cesar:
                    monitoring_json_block = {
                        "type": 'cesar',
                        "uid": item.unit_id,
                        "pin": item.pin,
                        "pos_x": item.pos_x,
                        "pos_y": item.pos_y,
                        "address": str(get_address_from_coords(item.pos_x, item.pos_y)),
                        "last_time": unix_to_moscow_time(item.last_time),
                        "online": online_check_cesar(item.last_time)
                    }
                    monitoring_json_response["monitoring"].append(monitoring_json_block)

            #Получение алертов
            alerts_json_response = {"alert": []}
            alerts = db.session.query(Alert).filter(Alert.uNumber == car.uNumber).order_by(
                Alert.date.desc()).all()
            for item in alerts:
                result = db.session.query(AlertType).filter(AlertType.alert_un == item.type).first()
                localization = result.localization if result else item.type
                alerts_json_append = {
                    "id": item.id,
                    "status": item.status,
                    "type": item.type,
                    "localization": localization,
                    "data": item.data,
                    "datetime": unix_to_moscow_time(item.date),
                    "comment": item.comment,
                    "comment_editor": item.comment_editor,
                    "comment_date_time": item.date_time_edit,
                    "comment_date_time_msk": unix_to_moscow_time(item.date_time_edit)
                }
                alerts_json_response["alert"].append(alerts_json_append)

            # Получение комментов
            comments_json_response = {"comments": []}
            comments = db.session.query(Comments).filter(Comments.uNumber == car.uNumber).order_by(Comments.datetime_unix.desc()).all()
            for item in comments:
                comments_json_append = {
                    "id": item.comment_id,
                    "author": item.author,
                    "text": item.text,
                    "datetime": unix_to_moscow_time(item.datetime_unix)
                }
                comments_json_response["comments"].append(comments_json_append)

            #Получение переходов
            transfers_json_response = {"transfers": []}
            transfers = db.session.query(TransferTasks).filter(TransferTasks.uNumber == car.uNumber).order_by(
                TransferTasks.date.desc()).all()
            for transfer in transfers:
                # Определяем тип изменения
                if transfer.old_storage != transfer.new_storage:
                    transfer_type = "Перемещение по складу"
                    old_value = storage_id_to_name(transfer.old_storage) or "—"
                    new_value = storage_id_to_name(transfer.new_storage) or "—"
                elif transfer.old_manager != transfer.new_manager:
                    transfer_type = "Изменение менеджера"
                    old_value = transfer.old_manager or "—"
                    new_value = transfer.new_manager or "—"
                elif transfer.old_client != transfer.new_client:
                    transfer_type = "Изменение клиента"
                    old_value = transfer.old_client or "—"
                    new_value = transfer.new_client or "—"
                else:
                    transfer_type = "Неизвестный тип"
                    old_value = "—"
                    new_value = "—"

                # Добавляем данные о передаче в список
                transfers_json_response["transfers"].append({
                    "date": unix_to_moscow_time(transfer.date),
                    "type": transfer_type,
                    "old_value": old_value,
                    "new_value": new_value
                })

            # Формирование результата
            result = {
                "transport": {
                    "lot_number": car.uNumber,
                    "storage_id": car.storage_id,
                    "model_id": car.model_id,
                    "manufacture_year": car.manufacture_year,
                    "vin": car.vin
                },
                "storage": {
                    "1c_id": storage.ID,
                    "name": storage.name,
                    "type": storage.type,
                    "region": storage.region,
                    "address": storage.address,
                    "organization": storage.organization
                },
                "transport_model": {
                    "1c_id": transport_model.id,
                    "type": transport_model.type,
                    "name": transport_model.name,
                    "lift_type": transport_model.lift_type,
                    "engine": transport_model.engine,
                    "country": transport_model.country,
                    "machine_type": transport_model.machine_type,
                    "brand": transport_model.brand,
                    "model": transport_model.model
                },
                "rent": {
                    "x": car.x,
                    "y": car.y,
                    "address": str(get_address_from_coords(car.x, car.y)),
                    "customer": car.customer,
                    "customer_contact": car.customer_contact,
                    "manager": car.manager
                },
                "car_setting:": {
                    "virtual_operator": car.alert_preset
                }
            }

            # Добавляем данные из monitoring_json_response и alerts_json_append к результату
            result.update(monitoring_json_response)
            result.update(alerts_json_response)
            result.update(comments_json_response)
            result.update(transfers_json_response)


            return result, 200
        except Exception as e:
            print(f"Error occurred: {e}")
            print(f"Car: {car}")
            print(f"Storage: {storage}")
            print(f"TransportModel: {transport_model}")
            return {"error": "An unexpected error occurred", "details": str(e)}, 500



@car_ns.route('/all_monitoring_cars')
class CarsResource(Resource):
    @car_ns.param('type', 'Тип транспортного средства', type=str)
    @car_ns.param('region', 'Регион', type=str)
    @car_ns.response(200, 'Успешно')
    @car_ns.response(404, 'Данные не найдены')
    @need_access(-1)
    def get(self):
        """Получение списка автомобилей с фильтрами"""
        filters = {
            'type': request.args.get('type', ''),
            'region': request.args.get('region', '')
        }

        user = User.query.filter_by(username=session['username']).first_or_404()
        allowed_uNumbers = get_all_access_transport(user.username)

        if not allowed_uNumbers:
            return {'message': 'No data found.'}, 404

        query = db.session.query(Transport, Storage, TransportModel).join(
            Storage, Transport.storage_id == Storage.ID).join(
            TransportModel, Transport.model_id == TransportModel.id)

        if filters['type']:
            query = query.filter(TransportModel.type.like(f'%{filters["type"]}%'))
        if filters['region']:
            query = query.filter(Storage.region.like(f'%{filters["region"]}%'))

        query = query.filter(Transport.uNumber.in_(allowed_uNumbers))

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

        if has_role_access(user.username, 'csp'):
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


@car_ns.route('/get_history')
class GetCarHistory(Resource):

    @car_ns.param('nm', 'Номер транспортного средства', _required=True)
    @car_ns.param('monitoring_system', 'Cesar OR Wialon', _required=False)
    @car_ns.param('block_number', 'UID для Виалона, PIN для Цезаря', _required=False)
    @car_ns.param('time_from', 'Время начала фильтрации (UNIX timestamp)', _required=True)
    @car_ns.param('time_to', 'Время окончания фильтрации (UNIX timestamp)', _required=True)
    @car_ns.response(200, 'Успешно')  # Указываем модель для ответа
    @car_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @car_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(-1)
    def get(self):
        """Получение истории автомобиля по номеру и времени"""
        nm = request.args.get('nm')
        time_from = request.args.get('time_from')
        time_to = request.args.get('time_to')
        monitoring_system = request.args.get('monitoring_system')
        block_number = request.args.get('block_number')

        valid_systems = {None, 'Wialon', 'Cesar'}
        if monitoring_system not in valid_systems:
            return {'error': f'Invalid monitoring_system value: {monitoring_system}. Valid values: {valid_systems}'}, 400

        if not nm or not time_from or not time_to:
            return {'error': 'Missing required parameters: nm, time_from, time_to'}, 400

        try:
            time_from_unix = int(time_from)
            time_to_unix = int(time_to)
        except ValueError as e:
            return {'error': f'Invalid timestamp format: {str(e)}'}, 400

        try:
            result = []

            wialon_query = db.session.query(CashHistoryWialon).filter(
                CashHistoryWialon.nm == nm,
                CashHistoryWialon.last_time >= time_from_unix,
                CashHistoryWialon.last_time <= time_to_unix
            )

            cesar_query = db.session.query(CashHistoryCesar).filter(
                CashHistoryCesar.nm == nm,
                CashHistoryCesar.last_time >= time_from_unix,
                CashHistoryCesar.last_time <= time_to_unix
            )

            if monitoring_system == 'Wialon' or monitoring_system is None:
                if block_number is not None:
                    wialon_query = wialon_query.filter(CashHistoryWialon.uid == block_number)

                wialon_entries = wialon_query.all()
                result = [
                    {
                        'uid': entry.uid,
                        'nm': entry.nm,
                        'pos_x': entry.pos_x,
                        'pos_y': entry.pos_y,
                        'last_time': entry.last_time,
                        'source': 'wialon'
                    }
                    for entry in wialon_entries
                ]

            if monitoring_system == 'Cesar' or monitoring_system is None:
                if block_number is not None:
                    cesar_query = cesar_query.filter(CashHistoryCesar.pin == block_number)

                cesar_entries = cesar_query.all()
                result += [
                    {
                        'uid': entry.pin,
                        'nm': entry.nm,
                        'pos_y': entry.pos_x,
                        'pos_x': entry.pos_y,
                        'last_time': entry.last_time,
                        'source': 'cesar'
                    }
                    for entry in cesar_entries
                ]

            result.sort(key=lambda x: x['last_time'])

            return result

        except Exception as e:
            print(f"Error occurred while fetching car history: {e}")
            return {'error': 'Database query failed'}, 500


@car_ns.route('/set_preset')
class SetPreset(Resource):
    @car_ns.param('uNumber', 'Номер транспортного средства (uNumber)', _required=True)
    @car_ns.param('alert_type_presets_id', 'ID пресета из AlertTypePresets (может быть null)', _required=False)
    @car_ns.response(200, 'Успешно')
    @car_ns.response(400, 'Неверный запрос (например, отсутствует uNumber или неверный alert_type_presets_id)')
    @car_ns.response(404, 'Транспорт или пресет не найден')
    @car_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access(-1)
    def put(self):
        """Установка или удаление пресета для транспорта по uNumber"""
        uNumber = request.args.get('uNumber')
        alert_type_presets_id = request.args.get('alert_type_presets_id')

        if not uNumber:
            return {'status': 'error', 'message': 'Не указан uNumber'}, 400

        try:
            # Проверяем существование транспорта
            transport = db.session.query(Transport).filter_by(uNumber=uNumber).first()
            if not transport:
                return {'status': 'error', 'message': f'Транспорт с uNumber {uNumber} не найден'}, 404

            # Если alert_type_presets_id не указан или пустой, устанавливаем NULL
            if alert_type_presets_id is None or alert_type_presets_id == '' or alert_type_presets_id.lower() == 'null':
                transport.alert_preset= None
            else:
                # Проверяем, существует ли пресет
                try:
                    alert_type_presets_id = int(alert_type_presets_id)
                    preset = db.session.query(AlertTypePresets).filter_by(id=alert_type_presets_id).first()
                    if not preset:
                        return {'status': 'error', 'message': f'Пресет с id {alert_type_presets_id} не найден'}, 404
                    transport.alert_preset = alert_type_presets_id
                except ValueError:
                    return {'status': 'error', 'message': 'alert_type_presets_id должен быть целым числом или null'}, 400
            print(transport.alert_preset, transport.uNumber)
            db.session.commit()
            return {'status': 'success', 'message': 'Пресет обновлен'}, 200

        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Ошибка при обновлении пресета: {str(e)}'}, 500