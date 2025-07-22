import ast
import json
import os
import time
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, send_file, g
import xml.etree.ElementTree as ET

from modules.my_time import online_check
from .models import db, User, Transport, TransportModel, Storage, CashWialon, CashCesar, Alert, Comments, TransferTasks, \
    IgnoredStorage, AlertType, ParserTasks
from .utils import need_access
from modules import report_generator, my_time, hash_password
from .utils.functionality_acccess import has_role_access
from .utils.transport_acccess import get_all_access_transport

# Создаем Blueprint для основных маршрутов приложения
bp = Blueprint('main', __name__)


@bp.before_request
def set_user():
    username = session.get('username')
    if username:
        g.user = User.query.filter_by(username=username).first()
    else:
        g.user = None


# Главная страница
@bp.route('/', endpoint='home')
@need_access(-2)
def home():
    # Получаем параметры фильтра из запроса
    filters = {
        'nm': request.args.get('nm'),
        'model': request.args.get('model'),
        'vin': request.args.get('vin'),
        'model_type': request.args.get('model_type'),
        'customer': request.args.get('customer'),
        'manager': request.args.get('manager'),
        'storage': request.args.get('storage'),
        'region': request.args.get('region'),
        'organization': request.args.get('organization'),
        'last_time_start': request.args.get('last_time_start'),
        'last_time_end': request.args.get('last_time_end'),
        'voperator': request.args.get('voperator'),
        '1cparser': request.args.get('1cparser'),
        'online': request.args.get('online')
    }

    # Создаем базовый запрос с объединением трех таблиц
    query = db.session.query(Transport, Storage, TransportModel, CashWialon).outerjoin(
        Storage, Transport.storage_id == Storage.ID
    ).outerjoin(
        TransportModel, Transport.model_id == TransportModel.id
    ).outerjoin(
        CashWialon, Transport.uNumber == CashWialon.nm
    )

    # Применяем фильтры к запросу
    if filters['nm']:
        query = query.filter(Transport.uNumber.like(f'%{filters["nm"]}%'))
    if filters['model']:
        query = query.filter(TransportModel.name.like(f'%{filters["model"]}%'))
    if filters['vin']:
        query = query.filter(Transport.vin.like(f'%{filters["vin"]}%'))
    if filters['model_type'] and filters['model_type'] != 'all':
        query = query.filter(TransportModel.type == filters["model_type"])
    if filters['storage']:
        query = query.filter(Storage.name.like(f'%{filters["storage"]}%'))
    if filters['region']:
        query = query.filter(Storage.region.like(f'%{filters["region"]}%'))
    if filters['organization']:
        query = query.filter(Storage.organization.like(f'%{filters["organization"]}%'))
    if filters['customer']:
        query = query.filter(Transport.customer.like(f'%{filters["customer"]}%'))
    if filters['manager']:
        query = query.filter(Transport.manager.like(f'%{filters["manager"]}%'))
    if filters['1cparser']:
        if filters['1cparser'] == 'no':
            query = query.filter(Transport.parser_1c == 0)
        elif filters['1cparser'] == 'yes':
            query = query.filter(Transport.parser_1c == 1)
    else:
        query = query.filter(Transport.parser_1c == 1)
    if filters['last_time_start'] or filters['last_time_end'] or filters['online']:

        last_time_start_unix = my_time.to_unix_time(filters['last_time_start']) if filters['last_time_start'] else 0
        last_time_end_unix = my_time.to_unix_time(filters['last_time_end']) if filters['last_time_end'] else time.time()
        if filters['online'] == 'no':
            if last_time_end_unix >= my_time.five_minutes_ago_unix():
                last_time_end_unix = my_time.five_minutes_ago_unix()
        if filters['online'] == 'yes':
            if last_time_start_unix == 0:
                last_time_start_unix = my_time.five_minutes_ago_unix()
        if not filters['online'] == 'all':
            query = query.filter(CashWialon.last_time.between(last_time_start_unix, last_time_end_unix))

    # Фильтруем транспорт по доступам пользователя
    allowed_uNumbers = get_all_access_transport(session['username'])
    if not allowed_uNumbers:
        return render_template('pages/search/page.html', columns=['№ Лота', 'Модель', 'Склад', 'Регион'], table_rows=[],
                               redi='/car/', request=request)

    query = query.filter(Transport.uNumber.in_(allowed_uNumbers if allowed_uNumbers else ['']))

    data_db = query.all()
    columns = ['№ Лота', 'Модель', 'Склад', 'Регион']
    columns_data = []
    seen_unumbers = set()  # Множество для отслеживания уникальных uNumber

    if data_db is not None:
        for transport, storage, transport_model, wialon in data_db:
            transport_number = transport.uNumber
            # Пропускаем запись, если uNumber уже встречался
            if transport_number in seen_unumbers:
                continue

            seen_unumbers.add(transport_number)
            transport_model_name = transport_model.name if transport_model else 'None'
            storage_name = storage.name if storage else 'None'
            storage_region = storage.region if storage else 'None'

            columns_data.append([transport_number, transport_model_name, storage_name, storage_region])

    # Отображаем шаблон с результатами фильтрации
    return render_template('pages/search/page.html', columns=columns, table_rows=columns_data, redi='/car/', request=request)


# Страница состояния
@bp.route('/virtual_operator')
@need_access(0)
def virtual_operator():
    distance = db.session.query(Alert).join(AlertType, Alert.type==AlertType.alert_un).filter(Alert.status == 0, Alert.type.in_(['distance', 'gps'])).order_by(Alert.date.desc()).all()
    no_docs_cord = db.session.query(Alert).join(AlertType, Alert.type == AlertType.alert_un).filter(Alert.status == 0, Alert.type == 'no_docs_cords').order_by(Alert.date.desc()).all()
    not_work = db.session.query(Alert).join(AlertType, Alert.type==AlertType.alert_un).filter(Alert.status == 0, Alert.type == 'not_work').order_by(Alert.date.desc()).all()
    no_equipment = db.session.query(Alert).join(AlertType, Alert.type==AlertType.alert_un).filter(Alert.status == 0, Alert.type == 'no_equipment').order_by(Alert.date.desc()).all()
    other = db.session.query(Alert).join(AlertType, Alert.type == AlertType.alert_un).filter(Alert.status == 0,
                                                                                             Alert.type.not_in(
                                                                                                 ['distance', 'gps',
                                                                                                  'no_docs_cords',
                                                                                                  'not_work',
                                                                                                  'no_equipment'])).order_by(Alert.date.desc()).all()
    last_100_alerts = db.session.query(Alert).join(AlertType, Alert.type==AlertType.alert_un).order_by(Alert.date.desc()).limit(100).all()
    return render_template('pages/virtual_operator/page.html',
                           distance=distance,
                           no_docs_cord=no_docs_cord,
                           not_work=not_work,
                           no_equipment=no_equipment,
                           other=other,
                           last_100_alerts=last_100_alerts)



# Дашборды
@bp.route('/dashboard')
@need_access(0)
def dashboard():
    cesar_access = has_role_access(g.user.username, 'csp')

    # Wialon
    online_count = db.session.query(CashWialon).filter(CashWialon.last_time >= my_time.five_minutes_ago_unix()).count()
    offline_count = db.session.query(CashWialon).filter(CashWialon.last_time < my_time.five_minutes_ago_unix()).count()
    offline_over_48_count = db.session.query(CashWialon).filter(
        CashWialon.last_time < my_time.seventy_two_ago_unix()).count()
    wialon = {
        'online': online_count,
        'offline': offline_count,
        'offline_over_48': offline_over_48_count
    }
    #розыск
    distance = len(db.session.query(Alert).filter(Alert.status == 0, Alert.type.in_(['distance', 'gps', 'no_docs_cords'])).all())

    # Cesar
    online_count = db.session.query(CashCesar).filter(
        CashCesar.last_time >= my_time.get_time_minus_twelve_days()).count()
    offline_count = db.session.query(CashCesar).filter(
        CashCesar.last_time < my_time.get_time_minus_twelve_days()).count()
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

    return render_template('pages/dashboard/page.html', wialon=wialon, connections=connections, cesar=cesar, distance=distance, cesar_access=cesar_access)


# Страница отчетов
@bp.route('/rep')
@need_access(0)
def reports():
    user = User.query.filter_by(username=session['username']).first_or_404()
    categories = [
        {
            "id": "main",
            "title": "Общий отчет",
            "reports": [
                {"id": "main_transport", "name": "Все транспортные средства"},
                {"id": "main_storage", "name": "Все склады"},
                {"id": "main_transport_model", "name": "Все модели ТС"},
                {"id": "main_summary", "name": "Сводный отчет с оборудованием"}
            ]
        },
        {
            "id": "health",
            "title": "Отчеты об обрудовании",
            "reports": [
                {"id": "health_coordinates", "name": "Сверка координат"},
                {"id": "health_no_equip", "name": "Лоты без оборудования"},
                {"id": "health_no_lot", "name": "Оборудование без лота"}
            ]
        },
        {
            "id": "dispatcher",
            "title": "Виртуальный диспетчер",
            "reports": [
                {"id": "vopereator_theft_risk", "name": "Опасность угона"},
                {"id": "vopereator_nonworking_equipment", "name": "Нерабочее оборудование"},
                {"id": "vopereator_no_equipment", "name": "Отсутствие оборудования"}
            ]
        },
        {
            "id": "wialon",
            "title": "Wialon",
            "reports": [
                {"id": "wialon", "name": "Весь транспорт"},
                {"id": "wialon_offline", "name": "Давно offline (от 3 дней)"},
                {"id": "wialon_with_address", "name": "Весь транспорт с адресом"}
            ]
        },
        {
            "id": "cesar",
            "title": "Cesar Position",
            "reports": [
                {"id": "cesar", "name": "Весь транспорт"},
                {"id": "cesar_offline", "name": "Давно offline (от 3 дней)"}
            ]
        },
    ]

    if not has_role_access(user.username, 'csp'):
        categories = [category for category in categories if category['id'] != 'cesar']

    return render_template('pages/reports/page.html', categories=categories)


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


@bp.route('/car/<string:car_id>')
@need_access(-1)
def car(car_id):
    text = car_id.replace(' ', '')
    if re.match(r'^[A-Z]+\d{5}$', text):
        if text[1] != ' ':
            car_id = text[:1] + ' ' + text[1:]
    car_name = f'{car_id}'
    ignored_storages = db.session.query(IgnoredStorage).all()

    return render_template(
        'pages/car/page.html',
        car_name=car_name,
        ignored_storages = ignored_storages
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


@bp.route('/maps/')
@need_access(-1)
def maps():
    return render_template('pages/maps/page.html')


@bp.route('/admin', methods=['GET'])
@need_access(1)
def admin_panel():
    return render_template('pages/admin_panel/page.html')


@bp.route('/admin/parser', methods=['GET'])
@need_access(1)
def parser_page():
    tasks_with_error_all = ParserTasks.query.filter(
        ParserTasks.task_completed == 0,
        ~ParserTasks.task_name.in_(['new_car', 'new_car_error'])
    ).all()
    tasks_with_error_new_car = ParserTasks.query.filter(
        ParserTasks.task_completed == 0,
        ParserTasks.task_name.in_(['new_car', 'new_car_error'])
    ).all()

    parsed_tasks = []
    for task in tasks_with_error_new_car:
        if not task.info:
            parsed_tasks.append({"id": task.id, "error": "Пустое содержимое XML"})
            continue
        try:
            root = ET.fromstring(task.info)
            task_data = {
                "id": task.id,
                "код_склада": root.attrib.get("КодСклада", "").strip() or "None",
                "склад": root.attrib.get("Склад", "").strip() or "None",
                "лот": root.attrib.get("Лот", "").strip() or "None",
                "ИДМодели": root.attrib.get("ИДМодели", "").strip() or "None",
                "серия": root.attrib.get("Серия", "").strip() or "None",
                "серия_год_выпуска": root.attrib.get("СерияГодВыпуска", "").strip() or "None",
                "широта": root.attrib.get("Широта", "").strip() or "0",
                "долгота": root.attrib.get("Долгота", "").strip() or "0",
                "контрагент": root.attrib.get("Контрагент", "").strip() or "None",
                "менеджер": root.attrib.get("ОтветственныйМенеджер", "").strip() or "None"
            }
            parsed_tasks.append(task_data)
        except Exception as e:
            parsed_tasks.append({"id": task.id, "error": f"Ошибка при обработке XML: {e}"})

    return render_template('pages/parser/page.html', tasks_with_error=tasks_with_error_all, parsed_tasks=parsed_tasks)