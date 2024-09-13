import json

from flask import Blueprint, request, jsonify, session
from . import db
from .utils import need_access, need_access
from .models import Transport, TransportModel, Storage, User, CashWialon

# Создаем Blueprint для API маршрутов приложения
api_bp = Blueprint('api', __name__)



@api_bp.route('/cars', methods=['GET'])
@need_access(-1)
def get_cars():
    # Получаем данные из базы
    data_db = db.session.query(CashWialon).all()

    # Фильтруем транспорт по доступам пользователя
    user = User.query.filter_by(username=session['username']).first_or_404()
    if user.role <= -1:
        user_access = json.loads(user.access)
        data_db = [item for item in data_db if item[0].manager in user_access]

    # Преобразуем данные в JSON
    cars_json = [{
        "nm": car.nm,
        "pos_x": car.pos_x,
        "pos_y": car.pos_y,
        "last_time": car.last_time
    } for car in data_db]

    return jsonify(cars_json)





