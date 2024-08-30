import time
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from .models import db, User, Transport, TransportModel, Storage, CashWialon, CashCesar, Alert
from .utils import login_required, admin_required
from modules import report_generator, my_time

# Создаем Blueprint для основных маршрутов приложения
bp = Blueprint('main', __name__)


# Главная страница
@bp.route('/', endpoint='home')
@login_required
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
@login_required
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
@login_required
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

    return render_template('pages/dashboard/page.html', wialon=wialon, connections=connections, cesar=cesar)


# Страница отчетов
@bp.route('/rep')
@login_required
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
        if user and user.password == password:
            session.permanent = True
            session['username'] = username
            return redirect(url_for('main.home'))
        else:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
    return render_template('standalone/login.html', error=error)


# Выход из системы
@bp.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


# Страница информации о конкретной машине
@bp.route('/cars/<string:car_id>')
@login_required
def get_car(car_id):
    text = car_id.replace(' ', '')
    if re.match(r'^[A-Z]+\d{5}$', text):
        if text[1] != ' ':
            car_id = text[:1] + ' ' + text[1:]
    search_pattern = f'%{car_id}%'

    wialon = db.session.query(CashWialon).filter(CashWialon.nm.like(search_pattern)).all()
    cesar = db.session.query(CashCesar).filter(CashCesar.object_name.like(search_pattern)).all()
    car = db.session.query(Transport).filter(Transport.uNumber == car_id).first()

    if not car:
        return "Car not found", 404

    storage = db.session.query(Storage).filter(Storage.ID == car.storage_id).first()
    transport_model = db.session.query(TransportModel).filter(TransportModel.id == car.model_id).first()

    return render_template(
        'pages/car/page.html',
        car=car,
        car_name=car_id,
        cesar=cesar,
        wialon=wialon,
        storage=storage,
        transport_model=transport_model,
    )


# Скачивание отчета
@bp.route('/download', endpoint="download")
@login_required
def download():
    report_name = request.args.get('report')

    if report_name == 'wialon_with_address':
        user = User.query.filter_by(username=session['username']).first_or_404()
        if user.role != 1:
            flash('Нет прав', 'warning')
            return redirect(url_for('main.home'))

    return report_generator.filegen(report_name)


@bp.route('/user_setting')
@login_required
def user_setting():
    user = User.query.filter_by(username=session['username']).first_or_404()
    return(render_template('pages/user_settings/page.html', user=user))


@bp.route('/map/')
@login_required
def map_page():
    wialon = db.session.query(CashWialon).all()
    cesar = db.session.query(CashCesar).all()
    return render_template('standalone/map.html', cesar=cesar, wialon=wialon)


@bp.route('/resources/transport')
@login_required
def transport_page():
    storages = Storage.query.all()
    models = TransportModel.query.all()
    return render_template('pages/resources/transport.html', storages=storages, models=models)


@bp.route('/resources/storage')
@login_required
def storage_page():
    storages = Storage.query.all()
    return render_template('pages/resources/storage.html', storages=storages)


@bp.route('/resources/models', methods=['GET'])
def models_page():
    return render_template('pages/resources/models.html')


