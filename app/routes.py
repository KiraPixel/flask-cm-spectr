import ast
import json
import os
import time
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, send_file

from .models import db, User, Transport, TransportModel, Storage, CashWialon, CashCesar, Alert, Comments
from .utils import need_access, need_access
from modules import report_generator, my_time, hash_password

# Создаем Blueprint для основных маршрутов приложения
bp = Blueprint('main', __name__)


# Главная страница
@bp.route('/', endpoint='home')
@need_access(-2)
def home():
    columns = ['№ Лота', 'Модель', 'Склад', 'Регион']
    columns_data = []

    # Получаем параметры фильтра из запроса
    filters = {
        'nm': request.args.get('nm'),
        'last_time_start': request.args.get('last_time_start'),
        'last_time_end': request.args.get('last_time_end'),
        'model': request.args.get('model'),
        'storage': request.args.get('storage'),
        'region': request.args.get('region')
    }

    # Создаем базовый запрос с объединением трех таблиц
    query = db.session.query(Transport, Storage, TransportModel).join(Storage, Transport.storage_id == Storage.ID).join(
        TransportModel, Transport.model_id == TransportModel.id)


    # Применяем фильтры к запросу
    if filters['nm']:
        query = query.filter(Transport.uNumber.like(f'%{filters["nm"]}%'))
    if filters['model']:
        query = query.filter(TransportModel.name.like(f'%{filters["model"]}%'))
    if filters['storage']:
        query = query.filter(Storage.name.like(f'%{filters["storage"]}%'))
    if filters['region']:
        query = query.filter(Storage.region.like(f'%{filters["region"]}%'))

    # Выполняем запрос и получаем данные
    data_db = query.all()

    # Фильтруем транспорт по доступам пользователя
    user = User.query.filter_by(username=session['username']).first_or_404()
    if user.role <= -1:
        user_access = json.loads(user.access)  # Предполагаем, что доступы хранятся в формате JSON
        data_db = [item for item in data_db if item[0].manager in user_access]

    # Обрабатываем фильтрацию по дате
    if filters['last_time_start'] or filters['last_time_end']:
        last_time_start_unix = my_time.to_unix_time(filters['last_time_start']) if filters['last_time_start'] else 0
        last_time_end_unix = my_time.to_unix_time(filters['last_time_end']) if filters['last_time_end'] else time.time()

        # Получаем данные из CashWialon в указанный временной интервал
        cash_wialon_data = db.session.query(CashWialon).filter(
            CashWialon.last_time.between(last_time_start_unix, last_time_end_unix)
        ).all()

        # Фильтруем данные на основе временного интервала
        filtered_data = []
        for transport, storage, transport_model in data_db:
            if any(data.nm.startswith(transport.uNumber) for data in cash_wialon_data):
                filtered_data.append((transport, storage, transport_model))
        data_db = filtered_data

    # Формируем данные для отображения
    for transport, storage, transport_model in data_db:
        columns_data.append([transport.uNumber, transport_model.name, storage.name, storage.region])

    # Отображаем шаблон с результатами фильтрации
    return render_template('pages/search/page.html', columns=columns, table_rows=columns_data, redi='/cars/', request=request)


# Страница состояния
@bp.route('/virtual_operator')
@need_access(0)
def virtual_operator():
    distance = db.session.query(Alert).filter(Alert.status == 0, Alert.type.in_(['distance', 'gps'])).order_by(Alert.date.desc()).all()
    not_work = db.session.query(Alert).filter(Alert.status == 0, Alert.type == 'not_work').order_by(Alert.date.desc()).all()
    no_equipment = db.session.query(Alert).filter(Alert.status == 0, Alert.type == 'no_equipment').order_by(Alert.date.desc()).all()
    last_100_alerts = db.session.query(Alert).order_by(Alert.date.desc()).limit(100).all()

    return render_template('pages/virtual_operator/page.html',
                           distance=distance,
                           not_work=not_work,
                           no_equipment=no_equipment,
                           last_100_alerts=last_100_alerts)



# Дашборды
@bp.route('/dashboard')
@need_access(0)
def dashboard():
    # Wialon
    online_count = db.session.query(CashWialon).filter(CashWialon.last_time >= my_time.five_minutes_ago_unix()).count()
    offline_count = db.session.query(CashWialon).filter(CashWialon.last_time < my_time.five_minutes_ago_unix()).count()
    offline_over_48_count = db.session.query(CashWialon).filter(
        CashWialon.last_time < my_time.forty_eight_hours_ago_unix()).count()
    wialon = {
        'online': online_count,
        'offline': offline_count,
        'offline_over_48': offline_over_48_count
    }
    #розыск
    distance = len(db.session.query(Alert).filter(Alert.status == 0, Alert.type.in_(['distance', 'gps'])).all())

    # Cesar
    online_count = db.session.query(CashWialon).filter(
        CashWialon.last_time >= my_time.get_time_minus_three_days()).count()
    offline_count = db.session.query(CashWialon).filter(
        CashWialon.last_time < my_time.get_time_minus_three_days()).count()
    cesar = {
        'online': online_count,
        'offline': offline_count
    }

    # Последнее подключение к Wialon
    last_wialon = db.session.query(CashWialon).order_by(CashWialon.last_time.desc()).first()
    last_wialon = last_wialon.last_time if last_wialon else None

    # Последнее подключение к Cesar
    last_cesar = db.session.query(CashCesar).order_by(CashCesar.last_time.desc()).first()
    if last_cesar.last_time > my_time.now_unix_time():
        last_cesar = my_time.now_unix_time()
    else:
        last_cesar = last_cesar.last_time if last_cesar else None
    connections = {
        'last_wialon': last_wialon,
        'last_cesar': last_cesar
    }

    return render_template('pages/dashboard/page.html', wialon=wialon, connections=connections, cesar=cesar, distance=distance)


# Страница отчетов
@bp.route('/rep')
@need_access(0)
def reports():
    return render_template('pages/reports/page.html')


# Страница входа
@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        print(f"UserLogin: {user}")
        if user is None:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
        elif hash_password.compare_passwords(user.password, password):
            session.permanent = True
            session['username'] = username
            return redirect(url_for('main.home'))
        else:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
    return render_template('standalone/login.html', error=error)


# Выход из системы
@bp.route('/logout')
@need_access(-2)
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


# Страница информации о конкретной машине
@bp.route('/cars/<string:car_id>')
@need_access(-1)
def get_car(car_id):
    text = car_id.replace(' ', '')
    if re.match(r'^[A-Z]+\d{5}$', text):
        if text[1] != ' ':
            car_id = text[:1] + ' ' + text[1:]
    search_pattern = f'%{car_id}%'

    wialon = db.session.query(CashWialon).filter(CashWialon.nm.like(search_pattern)).all()
    cesar = db.session.query(CashCesar).filter(CashCesar.object_name.like(search_pattern)).all()
    car = db.session.query(Transport).filter(Transport.uNumber == car_id).first()
    alerts = db.session.query(Alert).filter(Alert.uNumber == car_id).all()
    comments = db.session.query(Comments).filter(Comments.uNumber == car_id).all()

    if not car:
        return "Car not found", 404

    if wialon:
        # Обработка строковых данных
        wialon_cmd = ast.literal_eval((wialon[0].cmd) if wialon[0].cmd else {})
        wialon_sens = ast.literal_eval((wialon[0].sens) if wialon[0].sens else {})
    else:
        wialon_cmd = {}
        wialon_sens = {}

    storage = db.session.query(Storage).filter(Storage.ID == car.storage_id).first()
    transport_model = db.session.query(TransportModel).filter(TransportModel.id == car.model_id).first()

    return render_template(
        'pages/car/page.html',
        car=car,
        username=session['username'],
        car_name=car_id,
        cesar=cesar,
        wialon=wialon,
        storage=storage,
        transport_model=transport_model,
        wialon_cmd=wialon_cmd,
        wialon_sens=wialon_sens,
        alerts=alerts,
        comments=comments,
    )


# Скачивание отчета
@bp.route('/send_report', endpoint="send_report")
@need_access(0)
def send_report():
    report_name = request.args.get('report')
    print(f"Received report name: {report_name}")

    if not report_name:
        flash('Не указан отчет для отправки', 'warning')
        return redirect(url_for('main.home'))

    user = User.query.filter_by(username=session['username']).first_or_404()

    if report_name == 'wialon_with_address':
        if user.role != 1:
            flash('Нет прав', 'warning')
            return redirect(url_for('main.reports'))

    if report_generator.generate_and_send_report(report_name, user):
        flash('Отчет отправлен на почту', 'info')
        return redirect(url_for('main.reports'))
    else:
        flash('Произошла ошибка, обратитесь к системному администратору', 'warning')
        return redirect(url_for('main.reports'))



@bp.route('/map/')
@need_access(0)
def map_page():
    wialon = db.session.query(CashWialon).all()
    cesar = db.session.query(CashCesar).all()
    return render_template('standalone/map.html', cesar=cesar, wialon=wialon)


@bp.route('/maps/')
@need_access(-1)
def maps():
    # Выполняем запрос и получаем данные
    data_db = db.session.query(CashWialon).all()

    # Фильтруем транспорт по доступам пользователя
    user = User.query.filter_by(username=session['username']).first_or_404()
    if user.role <= -1:
        user_access = json.loads(user.access)
        data_db = [item for item in data_db if item[0].manager in user_access]

    return render_template('pages/maps/page.html')



