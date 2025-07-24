from functools import wraps

from flask import session, flash, redirect, url_for, request, g

from .functionality_acccess import get_user_roles
from ..models import db, User, Storage, Coord, AlertType, Transport
from modules import my_time, location_module
import datetime


def need_access(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Проверка на наличие API-ключа в запросе
            api_key = request.headers.get('X-API-KEY')

            if api_key:
                # Находим пользователя по API-ключу
                user_for_api_key = is_valid_api_key(api_key)

                if not user_for_api_key:
                    return 'invalid api key', 401

                # Если пользователь найден, записываем его в сессию
                user = user_for_api_key
                g.user = user
                session['username'] = user.username
                session.permanent = True

            # Проверка, есть ли в сессии 'username'
            if 'username' not in session:
                flash('Вы пытались зайти на страницу, к которой требуется авторизация.', 'warning')
                return redirect(url_for('main.login'))  # Редирект на страницу авторизации

            # Получаем пользователя из базы данных
            user = g.user

            # Устанавливаем текущее время для активности пользователя
            msk_time = datetime.datetime.fromtimestamp(my_time.now_unix_time(),
                                                       tz=datetime.timezone(datetime.timedelta(hours=3)))
            user.last_activity = msk_time.strftime('%Y-%m-%d %H:%M')

            if user.first_login == datetime.datetime(1999, 12, 2, 0, 0, 0):
                user.first_login = msk_time.strftime('%Y-%m-%d %H:%M')
            if user.password_activated_date == datetime.datetime(1999, 12, 2, 0, 0, 0):
                user.password_activated_date = msk_time.strftime('%Y-%m-%d %H:%M')
            db.session.commit()  # Сохраняем данные о времени последней активности


            # Проверяем роль пользователя
            if required_role not in get_user_roles(user):
                # Новая система ролирования
                if required_role != 'login':
                    if api_key:
                        return 'not accessed', 401
                    flash('Недостаточно прав для доступа', 'warning')
                    return redirect(url_for('main.home'))  # Редирект, если прав недостаточно


            # Если все проверки пройдены, вызываем основную функцию
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_address_from_coords(x, y):
    if not x or not y or x == 0 or y == 0:
        return "Convert error"

    # Округляем до 4 знаков после запятой
    x = float(f"{float(x):.4f}")
    y = float(f"{float(y):.4f}")

    # Ищем с небольшой погрешностью
    epsilon = 0.0001
    coord = Coord.query.filter(
        Coord.pos_x.between(x - epsilon, x + epsilon),
        Coord.pos_y.between(y - epsilon, y + epsilon)
    ).first()

    current_time = int(datetime.datetime.now().timestamp())
    six_months_seconds = 90 * 24 * 60 * 60 * 2

    if coord:
        if (current_time - coord.updated_time) <= six_months_seconds:
            return coord.address

    new_address = location_module.get_address(x, y)
    if new_address == "Convert error":
        return "Time out to convert"
    if coord:
        coord.address = new_address
        coord.updated_time = current_time
    else:
        new_coord = Coord(
            pos_x=x,
            pos_y=y,
            address=new_address,
            updated_time=current_time
        )
        db.session.add(new_coord)
    db.session.commit()
    return new_address

def storage_id_to_name(storage_id):
    storage = db.session.query(Storage).filter(Storage.ID == storage_id).first()
    if storage is None:
        storage_name = f'Неизвестный склад {storage_id}'
    else:
        storage_name = storage.name
    return storage_name


def is_valid_api_key(api_key):
    """
    Проверяет, существует ли ключ в базе данных и связан ли он с активным пользователем.
    """
    user = User.query.filter_by(api_token=api_key).first()
    if user:
        return user
    return None


def get_api_key_by_username(username):
    """
    Возвращает API ключ по имени пользователя.
    """
    user = User.query.filter_by(username=username).first()
    if user:
        return user.api_token
    return None


def get_alert_type(alert_name):
    """
    Возвращает инфу по алерту
    """
    class AlertObject():
        def __init__(self, alert_name):
            alert = AlertType.query.filter_by(alert_un=alert_name).first()
            self.alert_name = alert.alert_un
            self.localization = alert.localization
            self.criticality = alert.criticality
            self.category = alert.category


    return AlertObject(alert_name)




