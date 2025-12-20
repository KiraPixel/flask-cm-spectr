from flask import request, g
from flask_restx import Namespace, Resource, fields

from ..models import Reports, db
from ..utils import need_access

reports_ns = Namespace('reports', description='Генерация и отправка репортов')

# Модель для входных данных отчета
report_input_model = reports_ns.model('ReportInput', {
    'report_id': fields.String(required=True, description='ID репорта', example='custom_transport_transfer'),
    'date_from': fields.String(description='Дата начала (YYYY-MM-DD)', example='2025-08-01'),
    'date_to': fields.String(description='Дата окончания (YYYY-MM-DD)', example='2025-08-27'),
    'region': fields.String(description='Список регионов, разделенных запятой или новой строкой', example='Химки (г), Москва, СПБ'),
    'only_home_storages': fields.Boolean(description='Фильтровать только по домашним хранилищам', example=False)
})

# Модель для ответа
report_response_model = reports_ns.model('ReportResponse', {
    'message': fields.String(description='Сообщение о результате', example='Отчет отправлен на почту'),
    'success': fields.Boolean(description='Статус успешной операции', example=True)
})

@reports_ns.route('/get_report/', )
class GetReport(Resource):
    @reports_ns.doc(deprecated=True)
    @reports_ns.expect(report_input_model)
    @reports_ns.marshal_with(report_response_model)
    @need_access('reports')
    def post(self):
        """Генерировать и отправить отчет (УСТАРЕЛО)"""
        user = g.user
        data = request.json

        report_id = data.get('report_id')
        if not report_id:
            return {'message': 'Не указан отчет для отправки', 'success': False}, 400

        if report_id == 'with_address_wialon' and user.role != 1:
            return {'message': 'Нет прав для генерации этого отчета', 'success': False}, 403

        params = dict(data)
        params.pop('report_id', None)
        custom_params = {}
        if 'custom' in report_id:
            custom_params = {
                'date_from': params['date_from'],
                'date_to': params['date_to'],
                'region': params['region'],
                'only_home_storages': params['only_home_storages']
            }

        db_object = Reports(
            username=user.username,
            type=report_id,
            status='new',
            parameters=custom_params
        )
        db.session.add(db_object)
        db.session.commit()

        return {'message': 'Отчет поставлен на очередь генерации', 'success': True}, 200

reports_ns.add_resource(GetReport, '/get_report/')