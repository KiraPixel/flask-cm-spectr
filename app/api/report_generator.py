import os

from flask_restx import Namespace, Resource, fields
from flask import request, g
import httpx

from app import get_user_roles
from app.utils import need_access

report_api = Namespace("report_generator", description="Proxy to FastAPI Report Generator")
http_client = httpx.Client(
    base_url=os.getenv('REPORT_GENERATOR_URL', ''),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    timeout=httpx.Timeout(10.0, read=60.0)
)

report_gen_model = report_api.model('report_generator', {
    'report_name': fields.String(
        description='Название отчета',
        default='wialon'
    ),
    'username': fields.String(
        description='Имя пользователя (логин). Только админ может указывать не свой логин.',
        default='admin'
    ),
    'parameters': fields.Raw(
        description='Произвольный словарь параметров',
        default={"region": "Химки", "date_to": "2025-12-12", "date_from": "2025-12-10", "only_home_storages": 1},
    ),
    'send_to_mail': fields.Boolean(
        description='Требуется ли отправить отчет на почту',
        default=True
    )
})

@report_api.route("/report-list")
class ReportList(Resource):
    @need_access('reports')
    def get(self):
        resp = http_client.get("/report-list")
        return resp.json(), resp.status_code

@report_api.route("/report-categories")
class ReportCategories(Resource):
    @need_access('reports')
    def get(self):
        resp = http_client.get("/report-categories")
        if resp.status_code != 200:
            return resp.json(), resp.status_code

        all_reports = resp.json()

        user_roles = get_user_roles(g.user)

        filtered_reports = []
        for report in all_reports:
            required = report.get('need_access')

            if not required or required == 'admin' or required in user_roles:
                filtered_reports.append(report)

        return filtered_reports, 200

@report_api.route("/report-info/<int:report_id>")
class ReportInfo(Resource):
    @need_access('reports')
    def get(self, report_id):
        resp = http_client.get(f"/report-info/{report_id}")
        return resp.json(), resp.status_code


@report_api.route("/generate-report")
class GenerateReport(Resource):
    @need_access('reports')
    @report_api.expect(report_gen_model, validate=True)
    def post(self):
        incoming_data = request.get_json()

        report_name = incoming_data.get('report_name', None)
        if not report_name:
            return {'message': 'Не указан отчет для отправки'}, 400
        username = incoming_data.get('username', None)
        if g.user!=1 or username is None:
            username = g.user.username
        send_to_mail = incoming_data.get('send_to_mail', True)
        parameters = incoming_data.get('parameters', None)
        if parameters is None:
            exclude_fields = {'report_name', 'username', 'send_to_mail'}
            parameters = {k: v for k, v in incoming_data.items() if k not in exclude_fields}

        payload = {
            "report_name": report_name,
            "username": username,
            "parameters": parameters,
            "send_to_mail": send_to_mail
        }

        resp = http_client.post("/generate-report", json=payload)
        return resp.json(), resp.status_code