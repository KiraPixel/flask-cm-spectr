from flask import request
from flask_restx import Namespace, Resource, fields
import json

from sqlalchemy import and_

from app import db
from app.models import AlertTypePresets, Transport, AlertType
from app.utils import need_access

alerts_presets_ns = Namespace('alerts_presets', description='API для работы с пресетами оповещений и типами алертов')

# Модель для создания/обновления пресетов
preset_model = alerts_presets_ns.model('PresetModel', {
    'preset_name': fields.String(required=True, description='Название пресета'),
    'enable_alert_types': fields.List(fields.String, description='Список включенных типов оповещений'),
    'disable_alert_types': fields.List(fields.String, description='Список отключенных типов оповещений'),
    'jamming_zone': fields.Integer(description='Признак работы с зоне с глушилками', default=0),
    'wialon_danger_distance': fields.Integer(description='Опасное расстояние для Wialon (км)', default=5),
    'wialon_danger_hours_not_work': fields.Integer(description='Часы простоя для Wialon', default=72),
    'active': fields.Integer(description='Статус активности пресета (0 или 1)', default=1),
    'editable': fields.Integer(description='Статус редактируемости пресета (0 или 1)', default=1),
    'personalized': fields.Integer(description='Статус персонализации пресета (0 или 1)', default=0)
})

# Модель для получения пресета транспорта
vehicle_preset_model = alerts_presets_ns.model('VehiclePresetModel', {
    'uNumber': fields.String(required=True, description='Уникальный номер транспорта')
})

# Модель для получения типа алерта
alert_type_model = alerts_presets_ns.model('AlertTypeModel', {
    'alert_un': fields.String(required=True, description='Уникальный идентификатор типа алерта')
})

# Модель для получения транспорта по пресету
preset_vehicles_model = alerts_presets_ns.model('PresetVehiclesModel', {
    'preset_id': fields.String(required=True, description='ID пресета')
})


@alerts_presets_ns.route('')
class AlertsPresets(Resource):
    @alerts_presets_ns.doc(description="Получение всех пресетов оповещений")
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def get(self):
        """Получение всех пресетов оповещений"""
        try:
            presets = db.session.query(AlertTypePresets).all()
            result = [{
                'id': preset.id,
                'preset_name': preset.preset_name,
                'enable_alert_types': json.loads(preset.enable_alert_types) if preset.enable_alert_types else [],
                'disable_alert_types': json.loads(preset.disable_alert_types) if preset.disable_alert_types else [],
                'jamming_zone': preset.jamming_zone,
                'wialon_danger_distance': preset.wialon_danger_distance,
                'wialon_danger_hours_not_work': preset.wialon_danger_hours_not_work,
                'active': preset.active,
                'editable': preset.editable,
                'personalized': preset.personalized
            } for preset in presets]
            return {'status': 'success', 'data': result}, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении пресетов: {str(e)}'}, 500

    @alerts_presets_ns.doc(description="Создание нового пресета оповещений")
    @alerts_presets_ns.expect(preset_model)
    @alerts_presets_ns.response(200, 'Пресет успешно создан')
    @alerts_presets_ns.response(400, 'Неверный запрос')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def post(self):
        """Создание нового пресета оповещений"""
        data = request.json
        preset_name = data.get('preset_name')
        enable_alert_types = data.get('enable_alert_types', [])
        disable_alert_types = data.get('disable_alert_types', [])
        jamming_zone = data.get('jamming_zone')
        wialon_danger_distance = data.get('wialon_danger_distance', 5)
        wialon_danger_hours_not_work = data.get('wialon_danger_hours_not_work', 72)
        active = data.get('active', 1)
        editable = data.get('editable', 1)
        personalized = data.get('personalized', 0)

        # Проверка входных данных
        if not preset_name:
            return {'status': 'error', 'message': 'Требуется указать preset_name'}, 400

        if active not in [0, 1] or editable not in [0, 1] or personalized not in [0, 1] or jamming_zone not in [0, 1]:
            return {'status': 'error', 'message': 'Поля active, editable, personalized и jamming_zone должны быть 0 или 1'}, 400

        # Проверка валидности новых параметров
        if not isinstance(wialon_danger_distance, int) or wialon_danger_distance < 0:
            return {'status': 'error',
                    'message': 'wialon_danger_distance должно быть неотрицательным целым числом'}, 400
        if not isinstance(wialon_danger_hours_not_work, int) or wialon_danger_hours_not_work < 0:
            return {'status': 'error',
                    'message': 'wialon_danger_hours_not_work должно быть неотрицательным целым числом'}, 400

        # Проверка уникальности имени пресета
        if db.session.query(AlertTypePresets).filter_by(preset_name=preset_name).first():
            return {'status': 'error', 'message': f'Пресет с именем {preset_name} уже существует'}, 400

        try:
            new_preset = AlertTypePresets(
                preset_name=preset_name,
                enable_alert_types=json.dumps(enable_alert_types),
                disable_alert_types=json.dumps(disable_alert_types),
                jamming_zone=jamming_zone,
                wialon_danger_distance=wialon_danger_distance,
                wialon_danger_hours_not_work=wialon_danger_hours_not_work,
                active=active,
                editable=editable,
                personalized=personalized
            )
            db.session.add(new_preset)
            db.session.commit()
            return {'status': 'success', 'message': 'Пресет создан', 'id': new_preset.id}, 200
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Ошибка при создании пресета: {str(e)}'}, 500

@alerts_presets_ns.route('/<string:preset_id>')
class AlertPreset(Resource):
    @alerts_presets_ns.doc(description="Получение пресета по ID")
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(404, 'Пресет не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def get(self, preset_id):
        """Получение пресета по ID"""
        try:
            preset = db.session.query(AlertTypePresets).filter_by(id=preset_id).first()
            if not preset:
                return {'status': 'error', 'message': f'Пресет с id {preset_id} не найден'}, 404

            return {
                'status': 'success',
                'data': {
                    'id': preset.id,
                    'preset_name': preset.preset_name,
                    'enable_alert_types': json.loads(preset.enable_alert_types) if preset.enable_alert_types else [],
                    'disable_alert_types': json.loads(preset.disable_alert_types) if preset.disable_alert_types else [],
                    'jamming_zone': preset.jamming_zone,
                    'wialon_danger_distance': preset.wialon_danger_distance,
                    'wialon_danger_hours_not_work': preset.wialon_danger_hours_not_work,
                    'active': preset.active,
                    'editable': preset.editable,
                    'personalized': preset.personalized
                }
            }, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении пресета: {str(e)}'}, 500

    @alerts_presets_ns.doc(description="Удаление пресета")
    @alerts_presets_ns.response(200, 'Пресет успешно обновлен')
    @alerts_presets_ns.response(404, 'Пресет не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    def delete(self, preset_id):
        """Удаление пресета"""
        try:
            preset = db.session.query(AlertTypePresets).filter_by(id=preset_id).first()
            if not preset:
                return {'status': 'error', 'message': f'Пресет с id {preset_id} не найден'}, 404

            db.session.delete(preset)
            db.session.commit()

            return {
                'status': 'success',
                'data': 'success'
            }, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при удалении пресета: {str(e)}'}, 500

    @alerts_presets_ns.doc(description="Обновление пресета")
    @alerts_presets_ns.expect(preset_model)
    @alerts_presets_ns.response(200, 'Пресет успешно обновлен')
    @alerts_presets_ns.response(400, 'Неверный запрос')
    @alerts_presets_ns.response(403, 'Пресет не редактируемый')
    @alerts_presets_ns.response(404, 'Пресет не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def put(self, preset_id):
        """Обновление пресета"""
        try:
            preset = db.session.query(AlertTypePresets).filter_by(id=preset_id).first()
            if not preset:
                return {'status': 'error', 'message': f'Пресет с id {preset_id} не найден'}, 404

            if preset.editable != 1:
                return {'status': 'error', 'message': 'Пресет не редактируемый'}, 403

            data = request.json

            if 'preset_name' in data:
                if db.session.query(AlertTypePresets).filter(AlertTypePresets.preset_name == data['preset_name'],
                                                             AlertTypePresets.id != preset_id).first():
                    return {'status': 'error', 'message': f'Пресет с именем {data["preset_name"]} уже существует'}, 400
                preset.preset_name = data['preset_name']

            if 'wialon_danger_distance' in data:
                if not isinstance(data['wialon_danger_distance'], int) or data['wialon_danger_distance'] < 0:
                    return {'status': 'error',
                            'message': 'wialon_danger_distance должно быть неотрицательным целым числом'}, 400
                preset.wialon_danger_distance = data['wialon_danger_distance']

                if 'wialon_danger_hours_not_work' in data:
                    if not isinstance(data['wialon_danger_hours_not_work'], int) or data['wialon_danger_hours_not_work'] < 0:
                        return {'status': 'error',
                                'message': 'wialon_danger_hours_not_work должно быть неотрицательным целым числом'}, 400
                preset.wialon_danger_hours_not_work = data['wialon_danger_hours_not_work']

            if 'jamming_zone' in data:
                if data['jamming_zone'] not in [0, 1]:
                    return {'status': 'error', 'message': 'Поле jamming должно быть 0 или 1'}, 400
                preset.jamming_zone = data['jamming_zone']

            if 'active' in data:
                if data['active'] not in [0, 1]:
                    return {'status': 'error', 'message': 'Поле active должно быть 0 или 1'}, 400
                preset.active = data['active']

            if 'editable' in data:
                if data['editable'] not in [0, 1]:
                    return {'status': 'error', 'message': 'Поле editable должно быть 0 или 1'}, 400
                preset.editable = data['editable']

            if 'personalized' in data:
                if data['personalized'] not in [0, 1]:
                    return {'status': 'error', 'message': 'Поле personalized должно быть 0 или 1'}, 400
                preset.personalized = data['personalized']

            enable_alert_types = data.get('enable_alert_types', [])
            if not isinstance(enable_alert_types, list):
                return {'status': 'error', 'message': 'enable_alert_types должно быть списком'}, 400
            preset.enable_alert_types = json.dumps(enable_alert_types)

            disable_alert_types = data.get('disable_alert_types', [])
            if not isinstance(disable_alert_types, list):
                return {'status': 'error', 'message': 'disable_alert_types должно быть списком'}, 400
            preset.disable_alert_types = json.dumps(disable_alert_types)

            db.session.commit()
            return {'status': 'success', 'message': 'Пресет обновлен'}, 200
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Ошибка при обновлении пресета: {str(e)}'}, 500


@alerts_presets_ns.route('/with_vehicle_count')
class AlertsPresetsWithVehicleCount(Resource):
    @alerts_presets_ns.doc(description="Получение всех пресетов с количеством техники")
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def get(self):
        """Получение всех пресетов с их настройками и количеством транспорта"""
        try:
            # Получаем все пресеты
            presets = db.session.query(AlertTypePresets).all()

            # Получаем количество транспорта по каждому пресету одним запросом
            preset_counts = db.session.query(
                Transport.alert_preset,
                db.func.count(Transport.id)
            ).group_by(Transport.alert_preset).all()
            count_map = {preset_id: count for preset_id, count in preset_counts}

            # Формируем итоговый результат
            result = []
            for preset in presets:
                preset_id = preset.id
                vehicle_count = count_map.get(preset_id, 0)
                result.append({
                    'id': preset_id,
                    'preset_name': preset.preset_name,
                    'enable_alert_types': json.loads(preset.enable_alert_types) if preset.enable_alert_types else [],
                    'disable_alert_types': json.loads(preset.disable_alert_types) if preset.disable_alert_types else [],
                    'jamming_zone': preset.jamming_zone,
                    'wialon_danger_distance': preset.wialon_danger_distance,
                    'wialon_danger_hours_not_work': preset.wialon_danger_hours_not_work,
                    'active': preset.active,
                    'editable': preset.editable,
                    'personalized': preset.personalized,
                    'vehicle_count': vehicle_count
                })

            return {'status': 'success', 'data': result}, 200

        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении пресетов с количеством техники: {str(e)}'}, 500


@alerts_presets_ns.route('/vehicle')
class VehiclePreset(Resource):
    @alerts_presets_ns.doc(description="Получение пресета транспорта и пресета по умолчанию")
    @alerts_presets_ns.expect(vehicle_preset_model)
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(404, 'Транспорт не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def post(self):
        """Получение пресета транспорта и пресета по умолчанию по uNumber"""
        try:
            data = request.json
            uNumber = data.get('uNumber')
            if not uNumber:
                return {'status': 'error', 'message': 'Требуется указать uNumber'}, 400

            transport = db.session.query(Transport).filter_by(uNumber=uNumber).first()
            if not transport:
                return {'status': 'error', 'message': f'Транспорт с uNumber {uNumber} не найден'}, 404

            default_preset_id = 1 if transport.parser_1c == 1 else 0
            default_preset = db.session.query(AlertTypePresets).filter_by(id=default_preset_id).first()

            result = {
                'default_preset': {
                    'id': default_preset.id,
                    'preset_name': default_preset.preset_name,
                    'enable_alert_types': json.loads(
                        default_preset.enable_alert_types) if default_preset.enable_alert_types else [],
                    'disable_alert_types': json.loads(
                        default_preset.disable_alert_types) if default_preset.disable_alert_types else [],
                    'jamming_zone': default_preset.jamming_zone,
                    'wialon_danger_distance': default_preset.wialon_danger_distance,
                    'wialon_danger_hours_not_work': default_preset.wialon_danger_hours_not_work,
                    'active': default_preset.active,
                    'editable': default_preset.editable,
                    'personalized': default_preset.personalized
                }
            }

            if transport.alert_preset:
                custom_preset = db.session.query(AlertTypePresets).filter_by(id=transport.alert_preset).first()
                if custom_preset:
                    result['custom_preset'] = {
                        'id': custom_preset.id,
                        'preset_name': custom_preset.preset_name,
                        'enable_alert_types': json.loads(
                            custom_preset.enable_alert_types) if custom_preset.enable_alert_types else [],
                        'disable_alert_types': json.loads(
                            custom_preset.disable_alert_types) if custom_preset.disable_alert_types else [],
                        'jamming_zone': custom_preset.jamming_zone,
                        'wialon_danger_distance': custom_preset.wialon_danger_distance,
                        'wialon_danger_hours_not_work': custom_preset.wialon_danger_hours_not_work,
                        'active': custom_preset.active,
                        'editable': custom_preset.editable,
                        'personalized': custom_preset.personalized
                    }

            return {'status': 'success', 'data': result}, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении пресетов транспорта: {str(e)}'}, 500


@alerts_presets_ns.route('/alert_types')
class AlertTypes(Resource):
    @alerts_presets_ns.doc(description="Получение всех типов алертов")
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def get(self):
        """Получение всех типов алертов"""
        try:
            alert_types = db.session.query(AlertType).all()
            result = [{
                'alert_un': alert_type.alert_un,
                'localization': alert_type.localization,
                'criticality': alert_type.criticality,
                'category': alert_type.category
            } for alert_type in alert_types]
            return {'status': 'success', 'data': result}, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении типов алертов: {str(e)}'}, 500


@alerts_presets_ns.route('/alert_type/<string:alert_un>')
class AlertTypeById(Resource):
    @alerts_presets_ns.doc(description="Получение типа алерта по alert_un")
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(404, 'Тип алерта не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def get(self, alert_un):
        """Получение типа алерта по alert_un"""
        try:
            alert_type = db.session.query(AlertType).filter_by(alert_un=alert_un).first()
            if not alert_type:
                return {'status': 'error', 'message': f'Тип алерта с alert_un {alert_un} не найден'}, 404

            return {
                'status': 'success',
                'data': {
                    'alert_un': alert_type.alert_un,
                    'localization': alert_type.localization,
                    'criticality': alert_type.criticality,
                    'category': alert_type.category
                }
            }, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении типа алерта: {str(e)}'}, 500


@alerts_presets_ns.route('/vehicles_by_preset')
class VehiclesByPreset(Resource):
    @alerts_presets_ns.doc(description="Получение списка uNumber транспорта по ID пресета")
    @alerts_presets_ns.expect(preset_vehicles_model)
    @alerts_presets_ns.response(200, 'Успешно')
    @alerts_presets_ns.response(400, 'Неверный запрос')
    @alerts_presets_ns.response(404, 'Пресет не найден')
    @alerts_presets_ns.response(500, 'Ошибка базы данных')
    @need_access('admin_panel')
    def post(self):
        """Получение списка uNumber транспорта и их количества для указанного ID пресета"""
        try:
            data = request.json
            try:
                preset_id = int(data.get('preset_id'))
                if preset_id is None:
                    return {'status': 'error', 'message': 'Требуется указать preset_id'}, 400
            except Exception as e:
                return {'status': 'error', 'message': 'preset_id должен быть целым числом'}

            # Проверка существования пресета
            preset = db.session.query(AlertTypePresets).filter_by(id=preset_id).first()
            if not preset:
                return {'status': 'error', 'message': f'Пресет с id {preset_id} не найден'}, 404

            # Получение всех uNumber транспорта с указанным пресетом
            if preset_id <= 1:
                vehicles = db.session.query(Transport.uNumber).filter(and_(Transport.parser_1c==preset_id, Transport.alert_preset.is_(None))).all()
            else:
                vehicles = db.session.query(Transport.uNumber).filter_by(alert_preset=preset_id).all()
            u_numbers = [vehicle.uNumber for vehicle in vehicles]
            total_count = len(u_numbers)

            return {
                'status': 'success',
                'data': {
                    'u_numbers': u_numbers,
                    'total_count': total_count
                }
            }, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Ошибка при получении списка транспорта: {str(e)}'}, 500