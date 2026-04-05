import logging
import time
import re

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
import xml.etree.ElementTree as ET

from sqlalchemy import case

from .models import db, User, Transport, TransportModel, Storage, CashAxenta, CashCesar, Alert, \
    IgnoredStorage, AlertType, ParserTasks
from .utils import need_access
from modules import my_time, hash_password
from .utils.functionality_acccess import has_role_access
from .utils.transport_acccess import get_all_access_transport

# Создаем Blueprint
bp = Blueprint('main', __name__)
# Описываем основной логгер
logger = logging.getLogger('flask_cm_spectr')

@bp.before_request
def before_request():
    logger.debug(
        'Request: User=%s, Method=%s, URL=%s',
        g.user, request.method, request.url,
    )


# Главная страница
@bp.route('/', endpoint='home')
@need_access('login')
def home():
    return render_template('main.html')



# Дашборды
@bp.route('/dashboard')
@need_access('dashboard')
def dashboard():
    cesar_access = has_role_access(g.user.username, 'csp')

    # Axenta
    online_count = db.session.query(CashAxenta).filter(CashAxenta.last_time >= my_time.five_minutes_ago_unix()).count()
    offline_count = db.session.query(CashAxenta).filter(CashAxenta.last_time < my_time.five_minutes_ago_unix()).count()
    offline_over_48_count = db.session.query(CashAxenta).filter(
        CashAxenta.last_time < my_time.seventy_two_ago_unix()).count()
    axenta = {
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

    # Последнее подключение к Axenta
    last_axenta = db.session.query(CashAxenta).order_by(CashAxenta.last_time.desc()).first()
    last_axenta = last_axenta.last_time if last_axenta else None

    # Последнее подключение к Cesar
    last_cesar = db.session.query(CashCesar).order_by(CashCesar.last_time.desc()).first()
    if last_cesar.last_time > my_time.now_unix_time():
        last_cesar = my_time.now_unix_time()
    else:
        last_cesar = last_cesar.last_time if last_cesar else None
    connections = {
        'last_axenta': last_axenta,
        'last_cesar': last_cesar
    }

    return render_template('pages/dashboard/page.html', axenta=axenta, connections=connections, cesar=cesar, distance=distance, cesar_access=cesar_access)


# Страница входа
@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        session['username'] = username
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
        elif hash_password.compare_passwords(user.password, password):
            session.permanent = True
            g.user = user
            logging.info('UserLogin: username=%s', user.username)
            return redirect(url_for('main.home'))
        else:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
    return render_template('standalone/login.html', error=error)


# Выход из системы
@bp.route('/logout')
@need_access('login')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


@bp.route('/car/<string:car_id>')
@need_access('login')
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
        ignored_storages=ignored_storages
    )


@bp.route('/admin/', methods=['GET'])
@need_access('admin_panel')
def admin_panel():
    return render_template('pages/admin_panel/page.html')


@bp.route('/admin/parser', methods=['GET'])
@need_access('parser')
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