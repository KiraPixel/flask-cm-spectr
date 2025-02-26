from functools import wraps
from flask import session, flash, redirect, url_for, render_template, request
from .models import db, User, Storage
from modules import my_time
import datetime


def need_access(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Проверка на наличие API-ключа в запросе
            api_key = request.headers.get('X-API-KEY')

            if api_key:
                # Находим пользователя по API-ключу
                if not is_valid_api_key(api_key):
                    return 401
                user = User.query.filter_by(api_token=api_key).first()

                if user:
                    # Если пользователь найден, записываем его в сессию
                    session.permanent = True
                    session['username'] = user.username
                else:
                    # Если пользователя с таким ключом нет, возвращаем ошибку
                    flash('Неверный API-ключ', 'danger')
                    return redirect(url_for('main.home'))  # Редирект на главную страницу

            # Проверка, есть ли в сессии 'username'
            if 'username' not in session:
                flash('Вы пытались зайти на страницу, к которой требуется авторизация.', 'warning')
                return redirect(url_for('main.login'))  # Редирект на страницу авторизации

            # Получаем пользователя из базы данных
            user = User.query.filter_by(username=session['username']).first_or_404()

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
            if user.role < required_role:
                flash('Недостаточно прав для доступа', 'warning')
                return redirect(url_for('main.home'))  # Редирект, если прав недостаточно

            # Если все проверки пройдены, вызываем основную функцию
            return f(*args, **kwargs)

        return decorated_function

    return decorator



def storage_id_to_name(storage_id):
    storage = db.session.query(Storage).filter(Storage.ID == storage_id).first()
    return storage.name


def is_valid_api_key(api_key):
    """
    Проверяет, существует ли ключ в базе данных и связан ли он с активным пользователем.
    """
    user = User.query.filter_by(api_token=api_key).first()
    if user:
        return True
    return False


def get_api_key_by_username(username):
    """
    Возвращает API ключ по имени пользователя.
    """
    user = User.query.filter_by(username=username).first()
    if user:
        return user.api_token
    return None
