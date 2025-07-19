from flask import request
from flask_restx import Namespace, Resource, fields
from ..models import db, SystemSettings
from ..utils import need_access

settings_ns = Namespace('settings', description='System settings')

# Модель для системных настроек
system_settings_model = settings_ns.model('SystemSettings', {
    'enable_voperator': fields.Integer(description='Включение/выключение voperator: 0 (выключено), 1 (включено)'),
    'enable_xml_parser': fields.Integer(description='Включение/выключение XML-парсера: 0 (выключено), 1 (включено)'),
    'enable_db_cashing': fields.Integer(description='Включение/выключение кэширования базы данных: 0 (выключено), 1 (включено)')
}, description='Системные настройки приложения')

# Модель для входных данных
status_model = settings_ns.model('StatusModel', {
    'status': fields.Integer(required=True, description='Status value (0 or 1)', example=1)
})

# Получение системных настроек
@settings_ns.route('/system_settings')
class SystemSettingsAPI(Resource):
    @settings_ns.marshal_with(system_settings_model)
    @need_access(1)
    def get(self):
        """Получить текущие системные настройки"""
        settings = SystemSettings.query.first()
        return settings

class ChangeVOperatorStatus(Resource):
    @settings_ns.expect(status_model)
    @need_access(1)
    def post(self):
        data = request.json
        status = data.get('status')

        if status not in [0, 1]:
            return {'message': 'Status must be 0 or 1'}, 400

        row = db.session.query(SystemSettings).filter(SystemSettings.id == 0).first()
        row.enable_voperator = status
        db.session.commit()

        return {'message': 'VOperator status updated successfully', 'status': status}, 200

class ChangeXMLParserStatus(Resource):
    @settings_ns.expect(status_model)
    @need_access(1)
    def post(self):
        data = request.json
        status = data.get('status')

        if status not in [0, 1]:
            return {'message': 'Status must be 0 or 1'}, 400

        row = db.session.query(SystemSettings).filter(SystemSettings.id == 0).first()
        row.enable_xml_parser = status
        db.session.commit()

        return {'message': 'XMLParser status updated successfully', 'status': status}, 200


class ChangeDBCashingStatus(Resource):
    @settings_ns.expect(status_model)
    @need_access(1)
    def post(self):
        data = request.json
        status = data.get('status')

        if status not in [0, 1]:
            return {'message': 'Status must be 0 or 1'}, 400

        row = db.session.query(SystemSettings).filter(SystemSettings.id == 0).first()
        row.enable_db_cashing = status
        db.session.commit()

        return {'message': 'XMLParser status updated successfully', 'status': status}, 200

settings_ns.add_resource(ChangeVOperatorStatus, '/change_voperator_status')
settings_ns.add_resource(ChangeXMLParserStatus, '/change_xmlparser_status')
settings_ns.add_resource(ChangeDBCashingStatus, '/change_dbcashing_status')
