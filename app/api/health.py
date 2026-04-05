from flask_restx import Namespace, Resource
from sqlalchemy import func

from .. import cache
from ..models import User, CashAxenta, Alert, TransferTasks, db, SystemSettings
from modules.my_time import one_hours_ago_unix, forty_eight_hours_ago_unix

health_ns = Namespace('health', description='System health check')

@health_ns.route('')
class HealthCheck(Resource):
    @cache.cached(timeout=60, key_prefix='health_check_v1')
    def get(self):
        status_db = 0
        db_error = None
        settings = None

        try:
            db.session.execute(db.select(func.count(User.id)).limit(1)).scalar()
            status_db = 1
            settings = SystemSettings.query.first()
        except Exception as e:
            db_error = str(e)

        one_hour_ago = one_hours_ago_unix()
        two_days_ago = forty_eight_hours_ago_unix()

        cashing_module = 0
        last_axenta_time = "No data"

        if settings is None or settings.enable_db_cashing:
            try:
                last_ax = (
                    db.session.query(CashAxenta.last_time)
                    .order_by(CashAxenta.last_time.desc())
                    .limit(1)
                    .scalar()
                )
                if last_ax is not None and last_ax >= one_hour_ago:
                    cashing_module = 1
                    last_axenta_time = last_ax
            except Exception:
                pass

        voperator = 0
        last_alert_time = "No data"

        if settings is None or settings.enable_voperator:
            try:
                last_alert = (
                    db.session.query(Alert.date)
                    .order_by(Alert.date.desc())
                    .limit(1)
                    .scalar()
                )
                if last_alert is not None and int(last_alert) >= one_hour_ago:
                    voperator = 1
                    last_alert_time = last_alert
            except Exception:
                pass

        xml_parser = 0
        last_parser_time = "No data"

        if settings is None or settings.enable_xml_parser:
            try:
                last_task = (
                    db.session.query(TransferTasks.date)
                    .order_by(TransferTasks.date.desc())
                    .limit(1)
                    .scalar()
                )
                if last_task is not None and int(last_task) >= two_days_ago:
                    xml_parser = 1
                    last_parser_time = last_task
            except Exception:
                pass

        return {
            'status_db': {
                'status': status_db,
                'error': db_error
            },
            'cashing_module': {
                'status': cashing_module,
                'last_time': last_axenta_time
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