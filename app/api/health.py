from flask_restx import Namespace, Resource
from ..models import User, CashWialon, Alert, TransferTasks, db, SystemSettings
from modules.my_time import one_hours_ago_unix, forty_eight_hours_ago_unix

health_ns = Namespace('health', description='System health check')


@health_ns.route('')
class HealthCheck(Resource):
    def get(self):
        """Проверка состояния системы"""
        actual_settings = None
        try:
            db.session.query(User).first()
            status_db = 1
            db_error = None
            actual_settings = SystemSettings.query.first()
        except Exception as e:
            print(e)
            status_db = 0
            db_error = str(e)

        try:
            last_wialon_entry = CashWialon.query.order_by(CashWialon.last_time.desc()).first()
            if last_wialon_entry and last_wialon_entry.last_time >= one_hours_ago_unix():
                cashing_module = 1
                last_wialon_time = last_wialon_entry.last_time
            else:
                cashing_module = 0
                last_wialon_time = "No data"
            if actual_settings is not None:
                if not actual_settings.enable_db_cashing:
                    cashing_module = 0
        except Exception:
            cashing_module = 0
            last_wialon_time = "No data"

        try:
            last_alert_entry = Alert.query.order_by(Alert.date.desc()).first()
            if last_alert_entry and int(last_alert_entry.date) >= one_hours_ago_unix():
                voperator = 1
                last_alert_time = last_alert_entry.date
            else:
                voperator = 0
                last_alert_time = "No data"
            if actual_settings is not None:
                if not actual_settings.enable_voperator:
                    voperator = 0
        except Exception:
            voperator = 0
            last_alert_time = "No data"

        try:
            last_pars_entry = TransferTasks.query.order_by(TransferTasks.date.desc()).first()
            if last_pars_entry and int(last_pars_entry.date) >= forty_eight_hours_ago_unix():
                xml_parser = 1
                last_parser_time = last_pars_entry.date
            else:
                xml_parser = 0
                last_parser_time = "No data"
            if actual_settings is not None:
                if not actual_settings.enable_xml_parser:
                    xml_parser = 0
        except Exception:
            xml_parser = 0
            last_parser_time = "No data"

        return {
            'status_db': {
                'status': status_db,
                'error': db_error
            },
            'cashing_module': {
                'status': cashing_module,
                'last_time': last_wialon_time
            },
            'voperator_module': {
                'status': voperator,
                'last_time': last_alert_time
            },
            'xml_parser_module': {
                'status': xml_parser,
                'last_time': last_parser_time
            }
        }