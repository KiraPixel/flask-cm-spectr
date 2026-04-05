from flask import request, g
from flask_restx import Namespace, Resource, fields, reqparse, inputs
import time

from .. import db
from ..models import Transport, Storage, TransportModel, CashAxenta
from ..utils import need_access, my_time
from ..utils.transport_acccess import get_all_access_transport

search_ns = Namespace('search', description='Поиск и фильтрация транспорта')

transport_item = search_ns.model('TransportListItem', {
    'uNumber':        fields.String(description='№ лота / uNumber', example='T123456'),
    'model_name':     fields.String(description='Название модели',   example='MAN TGX 18.480', default='None'),
    'storage_name':   fields.String(description='Название склада',   example='Riga Main',      default='None'),
    'region':         fields.String(description='Регион',            example='Riga',           default='None'),
})

pagination_response = search_ns.model('TransportSearchResponse', {
    'items':     fields.List(fields.Nested(transport_item)),
    'page':      fields.Integer,
    'per_page':  fields.Integer,
    'has_more':  fields.Boolean,
})

parser = reqparse.RequestParser()

parser.add_argument('nm',           type=str, location='args')
parser.add_argument('model',        type=str, location='args')
parser.add_argument('vin',          type=str, location='args')
parser.add_argument('customer',     type=str, location='args')
parser.add_argument('manager',      type=str, location='args')
parser.add_argument('storage',      type=str, location='args')
parser.add_argument('region',       type=str, location='args')
parser.add_argument('organization', type=str, location='args')

parser.add_argument('model_type', type=str, location='args',
                    choices=['all', 'ПО', 'ПТО'], default='all')

parser.add_argument('1cparser', type=str, location='args',
                    choices=['yes', 'no', 'all'], default='yes')

parser.add_argument('online',           type=str, location='args',
                    choices=['yes', 'no', 'all'], default='all')
parser.add_argument('last_time_start',  type=inputs.date_from_iso8601, location='args')
parser.add_argument('last_time_end',    type=inputs.date_from_iso8601, location='args')

parser.add_argument('page',     type=int, default=1,  location='args')
parser.add_argument('per_page', type=int, default=25, location='args',
                    choices=[25, 50, 100, 500, 1000, 10000])

@search_ns.route('/transports')
class TransportSearch(Resource):

    @search_ns.expect(parser)
    @search_ns.marshal_with(pagination_response)
    @need_access('login')
    def get(self):
        args = parser.parse_args()

        filters = {
            'nm': args.get('nm'),
            'model': args.get('model'),
            'vin': args.get('vin'),
            'model_type': args.get('model_type'),
            'customer': args.get('customer'),
            'manager': args.get('manager'),
            'storage': args.get('storage'),
            'region': args.get('region'),
            'organization': args.get('organization'),
            '1cparser': args.get('1cparser'),
            'online': args.get('online'),
            'last_time_start': args.get('last_time_start'),
            'last_time_end': args.get('last_time_end'),
        }

        query = db.session.query(
            Transport.uNumber,
            TransportModel.name.label('model_name'),
            Storage.name.label('storage_name'),
            Storage.region.label('region')
        ).outerjoin(Storage, Transport.storage_id == Storage.ID
        ).outerjoin(TransportModel, Transport.model_id == TransportModel.id
        ).outerjoin(CashAxenta, Transport.uNumber == CashAxenta.nm)

        if filters['nm']:
            query = query.filter(Transport.uNumber.ilike(f"%{filters['nm'].rstrip()}%"))

        if filters['model']:
            query = query.filter(TransportModel.name.ilike(f"%{filters['model']}%"))

        if filters['vin']:
            query = query.filter(Transport.vin.ilike(f"%{filters['vin']}%"))

        if filters['model_type'] != 'all':
            query = query.filter(TransportModel.type == filters['model_type'])

        if filters['storage']:
            query = query.filter(Storage.name.ilike(f"%{filters['storage']}%"))

        if filters['region']:
            query = query.filter(Storage.region.ilike(f"%{filters['region']}%"))

        if filters['organization']:
            query = query.filter(Storage.organization.ilike(f"%{filters['organization']}%"))

        if filters['customer']:
            query = query.filter(Transport.customer.ilike(f"%{filters['customer']}%"))

        if filters['manager']:
            query = query.filter(Transport.manager.ilike(f"%{filters['manager']}%"))

        if filters['1cparser'] == 'yes':
            query = query.filter(Transport.parser_1c == 1)
        elif filters['1cparser'] == 'no':
            query = query.filter(Transport.parser_1c == 0)

        if filters['online'] != 'all' or filters['last_time_start'] or filters['last_time_end']:
            start_unix = my_time.to_unix_time(filters['last_time_start']) if filters['last_time_start'] else 0
            end_unix   = my_time.to_unix_time(filters['last_time_end'])   if filters['last_time_end']   else int(time.time())

            if filters['online'] == 'yes':
                query = query.filter(CashAxenta.connected_status == 1)
            elif filters['online'] == 'no':
                query = query.filter(CashAxenta.connected_status == 0)

            query = query.filter(CashAxenta.last_time.between(start_unix, end_unix))

        allowed_uNumbers = get_all_access_transport(g.user.username)
        if not allowed_uNumbers:
            return {
                'items': [],
                'page': args['page'],
                'per_page': args['per_page'],
                'has_more': False
            }

        query = query.filter(Transport.uNumber.in_(allowed_uNumbers))

        page = max(1, args['page'])
        per_page = args['per_page']
        offset = (page - 1) * per_page

        results = query.distinct(Transport.uNumber)\
                       .order_by(Transport.uNumber.asc())\
                       .offset(offset)\
                       .limit(per_page + 1)\
                       .all()

        items_list = results[:per_page]

        items = [
            {
                'uNumber':      r.uNumber,
                'model_name':   r.model_name or 'None',
                'storage_name': r.storage_name or 'None',
                'region':       r.region or 'None',
            }
            for r in items_list
        ]

        has_more = len(results) > per_page

        return {
            'items': items,
            'page': page,
            'per_page': per_page,
            'has_more': has_more
        }