from flask import g
from flask_restx import Namespace, Resource, fields
from sqlalchemy import case
from datetime import datetime, timezone

from .. import db
from ..models import Alert, AlertType, Transport, TransportModel
from ..utils import need_access
from ..utils.transport_acccess import get_all_access_transport

alerts_ns = Namespace('alerts', description='Активные алерты и последние алерты')

class UnixToIso(fields.Raw):
    def format(self, value):
        if value is None:
            return None
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (TypeError, ValueError):
            return None

alert_model = alerts_ns.model('Alert', {
    'id':           fields.Integer,
    'type':         fields.String,
    'date':         UnixToIso(description='ISO 8601 в UTC'),
    'status':       fields.Integer,
    'uNumber':      fields.String,
    'model_type':   fields.String(default=None),
    'comment':      fields.String(default=None),
    'data':         fields.String,
})

last_100_response = alerts_ns.model('Last100AlertsResponse', {
    'items': fields.List(fields.Nested(alert_model)),
    'total': fields.Integer,
})

active_alerts_response = alerts_ns.model('ActiveAlertsResponse', {
    'distance':       fields.List(fields.Nested(alert_model)),
    'no_docs_cords':   fields.List(fields.Nested(alert_model)),
    'not_work':       fields.List(fields.Nested(alert_model)),
    'no_equipment':   fields.List(fields.Nested(alert_model)),
    'other':          fields.List(fields.Nested(alert_model)),
    'total_active':   fields.Integer,
})

@alerts_ns.route('/last-100')
class Last100Alerts(Resource):
    @alerts_ns.marshal_with(last_100_response)
    @need_access('voperator')
    def get(self):
        allowed_un = get_all_access_transport(g.user.username)
        if not allowed_un:
            return {'items': [], 'total': 0}, 200

        query = (
            db.session.query(Alert, TransportModel.type.label('model_type'))
            .outerjoin(Transport, Alert.uNumber == Transport.uNumber)
            .outerjoin(TransportModel, Transport.model_id == TransportModel.id)
            .filter(Alert.uNumber.in_(allowed_un))
            .order_by(Alert.date.desc())
            .limit(100)
        )

        results = query.all()

        items = []
        for alert, model_type in results:
            alert.uNumber = alert.uNumber
            alert.model_type = model_type
            items.append(alert)

        return {
            'items': items,
            'total': len(items)
        }

@alerts_ns.route('/active')
class ActiveAlerts(Resource):
    @alerts_ns.marshal_with(active_alerts_response)
    @need_access('voperator')
    def get(self):
        allowed_un = get_all_access_transport(g.user.username)
        if not allowed_un:
            empty = {'distance': [], 'no_docs_cords': [], 'not_work': [], 'no_equipment': [], 'other': []}
            return {**empty, 'total_active': 0}, 200

        category_case = case(
            (Alert.type.in_(["distance", "gps"]), "distance"),
            (Alert.type == "no_docs_cords", "no_docs_cords"),
            (Alert.type == "not_work", "not_work"),
            (Alert.type == "no_equipment", "no_equipment"),
            else_="other"
        )

        query = (
            db.session.query(Alert, category_case.label("category"), TransportModel.type.label('model_type'))
            .outerjoin(Transport, Alert.uNumber == Transport.uNumber)
            .outerjoin(TransportModel, Transport.model_id == TransportModel.id)
            .join(AlertType, Alert.type == AlertType.alert_un)
            .filter(Alert.status == 0)
            .filter(Alert.uNumber.in_(allowed_un))
            .order_by(Alert.date.desc())
        )

        results = query.all()

        categories = {
            "distance": [],
            "no_docs_cords": [],
            "not_work": [],
            "no_equipment": [],
            "other": []
        }

        for alert, cat, model_type in results:
            alert.uNumber = alert.uNumber
            alert.model_type = model_type
            categories[cat].append(alert)

        total_active = sum(len(lst) for lst in categories.values())

        return {
            'distance':       categories["distance"],
            'no_docs_cords':   categories["no_docs_cords"],
            'not_work':       categories["not_work"],
            'no_equipment':   categories["no_equipment"],
            'other':          categories["other"],
            'total_active':   total_active
        }