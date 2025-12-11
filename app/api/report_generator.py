import os

from flask_restx import Namespace, Resource, fields
from flask import request
import httpx

from app.utils import need_access

report_api = Namespace("report_generator", description="Proxy to FastAPI Report Generator")
FASTAPI_URL = os.getenv('REPORT_GENERATOR_URL', None)


report_gen_model = report_api.model('report_generator', {
    'type': fields.String(
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

@report_api.route("/report-types")
class ReportTypes(Resource):
    @need_access('login')
    def get(self):
        with httpx.Client() as client:
            resp = client.get(f"{FASTAPI_URL}/report-types")
            return resp.json(), resp.status_code


@report_api.route("/report-info/<int:report_id>")
class ReportInfo(Resource):
    @need_access('login')
    def get(self, report_id):
        with httpx.Client() as client:
            resp = client.get(f"{FASTAPI_URL}/report-info/{report_id}")
            return resp.json(), resp.status_code


@report_api.route("/generate-report")
class GenerateReport(Resource):
    @need_access('login')
    @report_api.expect(report_gen_model, validate=True)
    def post(self):
        payload = request.get_json()
        with httpx.Client() as client:
            resp = client.post(
                f"{FASTAPI_URL}/generate-report",
                json=payload
            )
            return resp.json(), resp.status_code
