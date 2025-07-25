from flask import request, session, jsonify
from flask_restx import Namespace, Resource, fields

from app import db
from app.models import Transport, TransportModel, Storage, ParserTasks
from app.utils import need_access

parser_ns = Namespace('parser', description='Parser commands API')


add_new_car_model = parser_ns.model('AddNewCarModel', {
    'uNumber': fields.String(required=True, description='Номер транспортного средства'),
    'model_id': fields.String(required=True, description='ID модели транспортного средства'),
    'storage_id': fields.Integer(required=True, description='ID склада'),
    'VIN': fields.String(required=True, description='VIN номер транспортного средства'),
    'year': fields.String(required=True, description='Код выпуска'),
    'customer': fields.String(description='Имя клиента'),
    'manager': fields.String(description='Менеджер, ответственный за транспорт'),
    'x': fields.Float(description='Координата x'),
    'y': fields.Float(description='Координата y'),
    'parser_1c': fields.Integer(required=True, description='Есть ли ТС в парсере 1С (0 или 1)'),
})

@parser_ns.route('/add_new_car')
class AddNewCar(Resource):
    @parser_ns.doc(description="Добавление нового автомобиля")
    @parser_ns.expect(add_new_car_model)
    @parser_ns.response(200, 'Успешно добавлено')
    @parser_ns.response(400, 'Неверный запрос (например, отсутствуют параметры)')
    @parser_ns.response(500, 'Ошибка при выполнении запроса к базе данных')
    @need_access('parser')
    def post(self):
        """Добавление нового автомобиля"""
        data = request.json
        uNumber = data.get('uNumber')
        model_id = data.get('model_id')
        storage_id = data.get('storage_id')
        VIN = data.get('VIN')
        year = data.get('year')
        customer = data.get('customer')
        manager = data.get('manager')
        x = data.get('x')
        y = data.get('y')
        parser_1c = data.get('parser_1c') or 0

        # Проверка, что parser_1c равен 0 или 1
        if parser_1c not in [0, 1]:
            return {'status': 'error', 'message': 'parser_1c должен быть 0 или 1'}, 400

        # Проверка уникальности uNumber
        if db.session.query(Transport).filter_by(uNumber=uNumber).first():
            return {'status': 'error', 'message': f'uNumber {uNumber} уже существует'}, 400

        # Проверка, что model_id существует в таблице transport_model
        if not db.session.query(TransportModel).filter_by(id=model_id).first():
            return {'status': 'error', 'message': f'Не найден transport_model с id {model_id}'}, 400

        # Проверка, что storage_id существует в таблице storage
        if not db.session.query(Storage).filter_by(ID=storage_id).first():
            return {'status': 'error', 'message': f'Не найден storage с ID {storage_id}'}, 400

        # Проверка длины VIN
        if not (4 <= len(VIN) <= 22):
            return {'status': 'error', 'message': 'VIN должен быть длиной от 4 до 22 символов'}, 400

        # Проверка типов для x и y (должны быть числа с плавающей точкой)
        try:
            x = float(x)
            y = float(y)
        except ValueError:
            return {'status': 'error', 'message': 'x и y должны быть числами с плавающей точкой'}, 400

        # Добавление записи в базу данных
        new_car = Transport(
            uNumber=uNumber,
            model_id=model_id,
            storage_id=storage_id,
            vin=VIN,
            customer=customer,
            manager=manager,
            manufacture_year=year,
            x=x,
            y=y,
            parser_1c=parser_1c
        )

        try:
            db.session.add(new_car)
            db.session.commit()
            # Обновление статуса задач
            tasks = db.session.query(ParserTasks).filter(
                ParserTasks.task_name.in_(['new_car', 'new_car_error']),
                ParserTasks.variable == uNumber,
                ParserTasks.task_completed == 0,
            ).all()

            for task in tasks:
                task.task_completed = 1
                task.task_manager = g.user

            if tasks:
                db.session.commit()

            return {'status': 'success', 'message': 'Машина добавлена'}, 200
        except Exception as e:
            db.session.rollback()
            return {'status': 'error', 'message': f'Ошибка добавления машины: {str(e)}'}, 500


close_task = parser_ns.model('CloseTask', {
    'task_id': fields.Integer(required=True, description='Номер транспортного средства'),
})

@parser_ns.route('/close_task')
class CloseTask(Resource):
    @parser_ns.expect(close_task)
    @need_access('parser')
    def post(self):
        data = request.json
        task_id = data.get('task_id')

        if not task_id:
            return jsonify({'error': 'task_id is required'})

        task = db.session.query(ParserTasks).filter_by(id=task_id, task_completed=0).first()

        if not task:
            return jsonify({'error': f'Задача с id {task_id} не найдена или уже закрыта'})

        # Обновляем статус задачи на 1 (закрыта)
        task.task_completed = 1

        try:
            db.session.commit()
            return jsonify({'status': 'task closed'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Ошибка при закрытии задачи: {str(e)}'})
