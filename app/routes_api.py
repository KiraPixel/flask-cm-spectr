from flask import Blueprint, request, jsonify
from . import db
from .utils import login_required, need_access
from .models import Transport, TransportModel, Storage

# Создаем Blueprint для API маршрутов приложения
api_bp = Blueprint('api', __name__)


@api_bp.route('/search_transport')
@login_required
@need_access(1)
def search_transport():
    uNumber = request.args.get('uNumber')
    transports = Transport.query.filter(Transport.uNumber.like(f'%{uNumber}%')).all()
    results = []
    for transport in transports:
        results.append({
            'id': transport.id,
            'uNumber': transport.uNumber,
            'storage': {'ID': transport.storage.ID, 'name': transport.storage.name},
            'transport_model': {'id': transport.transport_model.id, 'name': transport.transport_model.name}
        })
    return jsonify(results)


@api_bp.route('/get_transport')
@login_required
@need_access(1)
def get_transport():
    transport_id = request.args.get('id')
    transport = Transport.query.get(transport_id)
    storages = Storage.query.all()
    models = TransportModel.query.all()
    result = {
        'id': transport.id,
        'uNumber': transport.uNumber,
        'storage_id': transport.storage_id,
        'model_id': transport.model_id,
        'storages': [{'ID': s.ID, 'name': s.name} for s in storages],
        'models': [{'id': m.id, 'name': m.name} for m in models]
    }
    return jsonify(result)


@api_bp.route('/add_transport', methods=['POST'])
@login_required
@need_access(1)
def add_transport():
    data = request.json
    uNumber = data['uNumber']
    existing_transport = Transport.query.filter_by(uNumber=uNumber).first()
    if existing_transport:
        return jsonify({'success': False, 'message': 'Транспорт с таким номером уже существует.'})

    new_transport = Transport(
        uNumber=uNumber,
        storage_id=data['storage_id'],
        model_id=data['model_id']
    )
    db.session.add(new_transport)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/update_transport', methods=['POST'])
@login_required
@need_access(1)
def update_transport():
    transport_id = request.form['id']
    transport = Transport.query.get(transport_id)

    if not transport:
        return jsonify({'success': False, 'message': 'Транспорт не найден.'})

    transport.uNumber = request.form['uNumber']
    transport.storage_id = request.form['storage_id']
    transport.model_id = request.form['model_id']

    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/search_storage', methods=['GET'])
@login_required
@need_access(1)
def search_storage():
    name_query = request.args.get('name', '')
    storages = Storage.query.filter(Storage.name.ilike(f'%{name_query}%')).all()
    return jsonify([{
        'ID': storage.ID,
        'name': storage.name,
        'type': storage.type,
        'region': storage.region,
        'address': storage.address,
        'organization': storage.organization
    } for storage in storages])


@api_bp.route('/get_storage', methods=['GET'])
@login_required
@need_access(1)
def get_storage():
    storage_id = request.args.get('id')
    storage = Storage.query.get(storage_id)
    if not storage:
        return jsonify({'success': False, 'message': 'Склад не найден.'})

    return jsonify({
        'ID': storage.ID,
        'name': storage.name,
        'type': storage.type,
        'region': storage.region,
        'address': storage.address,
        'organization': storage.organization
    })


@api_bp.route('/add_storage', methods=['POST'])
@login_required
@need_access(1)
def add_storage():
    data = request.json
    existing_storage = Storage.query.filter_by(name=data['name']).first()
    if existing_storage:
        return jsonify({'success': False, 'message': 'Склад с таким именем уже существует.'})

    new_storage = Storage(
        name=data['name'],
        type=data['type'],
        region=data['region'],
        address=data['address'],
        organization=data['organization']
    )
    db.session.add(new_storage)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/update_storage', methods=['POST'])
@login_required
@need_access(1)
def update_storage():
    data = request.form
    storage = Storage.query.get(data['ID'])

    if not storage:
        return jsonify({'success': False, 'message': 'Склад не найден.'})

    storage.name = data['name']
    storage.type = data['type']
    storage.region = data['region']
    storage.address = data['address']
    storage.organization = data['organization']

    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/delete_storage', methods=['POST'])
@login_required
@need_access(1)
def delete_storage():
    data = request.json
    storage_id = data['ID']
    storage = Storage.query.get(storage_id)

    if not storage:
        return jsonify({'success': False, 'message': 'Склад не найден.'})

    db.session.delete(storage)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/search_model', methods=['POST'])
@login_required
@need_access(1)
def search_model():
    data = request.json
    name = data.get('name', '')
    models = TransportModel.query.filter(TransportModel.name.ilike(f'%{name}%')).all()
    return jsonify([{
        'id': model.id,
        'name': model.name,
        'type': model.type,
        'lift_type': model.lift_type,
        'engine': model.engine
    } for model in models])


@api_bp.route('/add_model', methods=['POST'])
@login_required
@need_access(1)
def add_model():
    data = request.json
    new_model = TransportModel(
        type=data.get('type'),
        name=data.get('name'),
        lift_type=data.get('lift_type'),
        engine=data.get('engine')
    )
    db.session.add(new_model)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/delete_model', methods=['POST'])
@login_required
@need_access(1)
def delete_model():
    data = request.json
    model_id = data.get('id')
    model = TransportModel.query.get(model_id)
    if model:
        db.session.delete(model)
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Модель не найдена'})


@api_bp.route('/get_model', methods=['GET'])
@login_required
@need_access(1)
def get_model():
    model_id = request.args.get('id')
    model = TransportModel.query.get(model_id)
    if model:
        return jsonify({
            'id': model.id,
            'name': model.name,
            'type': model.type,
            'lift_type': model.lift_type,
            'engine': model.engine
        })
    else:
        return jsonify({'success': False, 'message': 'Модель не найдена'})


@api_bp.route('/update_model', methods=['POST'])
@login_required
@need_access(1)
def update_model():
    data = request.json
    model_id = data.get('id')
    model = TransportModel.query.get(model_id)
    if model:
        model.type = data.get('type')
        model.name = data.get('name')
        model.lift_type = data.get('lift_type')
        model.engine = data.get('engine')
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Модель не найдена'})
