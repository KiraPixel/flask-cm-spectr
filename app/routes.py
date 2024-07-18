from datetime import datetime
import time
import re

from flask import Blueprint, render_template, request, send_file, redirect, url_for, session, flash

from . import Jira
from .models import db, User, Transport, Storage, CashWialon, CashCesar
from .utils import login_required, admin_required
from .modules import ReportGenerator, MyTime, DBcash
from custom_api.wialon import WialonSearcher

# Создаем Blueprint для маршрутов приложения
bp = Blueprint('main', __name__)


# Главная страница
@bp.route('/', endpoint='home')
@login_required
def home():
    DBcash.UpdateBD()
    columns = ['№ Лота', 'Модель', 'Склад', 'Регион']  # Заголовки столбцов
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

    # Создаем базовый запрос
    query = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID)

    # Применяем фильтры к запросу
    if filters['nm']:
        query = query.filter(Transport.uNumber.like(f'%{filters["nm"]}%'))
    if filters['model']:
        query = query.filter(Transport.model.like(f'%{filters["model"]}%'))
    if filters['storage']:
        query = query.filter(Storage.name.like(f'%{filters["storage"]}%'))
    if filters['region']:
        query = query.filter(Storage.region.like(f'%{filters["region"]}%'))

    # Выполняем запрос и получаем данные
    data_db = query.all()

    # Обрабатываем фильтрацию по дате
    if filters['last_time_start'] or filters['last_time_end']:
        last_time_start_unix = MyTime.to_unix_time(filters['last_time_start']) if filters['last_time_start'] else 0
        last_time_end_unix = MyTime.to_unix_time(filters['last_time_end']) if filters['last_time_end'] else time.time()

        # Получаем данные из CashWialon в указанный временной интервал
        cash_wialon_data = db.session.query(CashWialon).filter(
            CashWialon.last_time.between(last_time_start_unix, last_time_end_unix)
        ).all()

        # Фильтруем данные на основе временного интервала
        filtered_data = []
        for transport, storage in data_db:
            if any(data.nm.startswith(transport.uNumber) for data in cash_wialon_data):
                filtered_data.append((transport, storage))
        data_db = filtered_data

    # Формируем данные для отображения
    for transport, storage in data_db:
        columns_data.append([transport.uNumber, transport.model, storage.name, storage.region])

    # Отображаем шаблон с результатами фильтрации
    return render_template('filter.html', columns=columns, table_rows=columns_data, redi='/cars/', request=request)


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
    return render_template('login.html', error=error)


# Выход из системы
@bp.route('/logout')
@login_required  # Декоратор, требующий авторизации для доступа к странице
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


# Страница отчетов
@bp.route('/rep')
@login_required  # Декоратор, требующий авторизации для доступа к странице
def reports():
    return render_template('reports.html')


# Страница информации о конкретной машине
@bp.route('/cars/<string:car_id>')
@login_required  # Декоратор, требующий авторизации для доступа к странице
def get_car(car_id):
    text = car_id.replace(' ', '')
    if re.match(r'^[A-Z]+\d{5}$', text):
        # Добавляем пробел перед цифрами, если его нет
        if text[1] != ' ':
            car_id = text[:1] + ' ' + text[1:]
    search_pattern = f'%{car_id}%'

    #получаем полный набор данных
    wialon = db.session.query(CashWialon).filter(CashWialon.nm.like(search_pattern)).all()
    cesar = db.session.query(CashCesar).filter(CashCesar.object_name.like(search_pattern)).all()
    jira_info = Jira.search(search_pattern)
    return render_template('car.html', car_name=car_id, cesar=cesar, wialon=wialon, jira=jira_info)


# Скачивание отчета
@bp.route('/download', endpoint="download")
@login_required  # Декоратор, требующий авторизации для доступа к странице
def download():
    report_name = request.args.get('report')
    return ReportGenerator.filegen(report_name)


# Панель администратора
@bp.route('/admin/', methods=['GET', 'POST'])
@login_required  # Декоратор, требующий авторизации для доступа к странице
@admin_required  # Декоратор, требующий прав администратора для доступа к странице
def admin_panel():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        # Создаем нового пользователя
        new_user = User(username=username, email=email, password=password, role=role, last_activity="1999-12-02 00:00:00")
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.admin_panel'))

    # Получаем список всех пользователей
    users = User.query.all()
    return render_template('admin_panel.html', users=users)


# Редактирование пользователя
@bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required  # Декоратор, требующий авторизации для доступа к странице
@admin_required  # Декоратор, требующий прав администратора для доступа к странице
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        return redirect(url_for('main.admin_panel'))

    return render_template('edit_user.html', user=user)


# Удаление пользователя
@bp.route('/delete_user/<int:user_id>')
@login_required  # Декоратор, требующий авторизации для доступа к странице
@admin_required  # Декоратор, требующий прав администратора для доступа к странице
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('main.admin_panel'))


# Назначение доступов пользователю
@bp.route('/set_access/<int:user_id>')
@login_required  # Декоратор, требующий авторизации для доступа к странице
@admin_required  # Декоратор, требующий прав администратора для доступа к странице
def set_access(user_id):
    user = User.query.get_or_404(user_id)
    # Логика назначения доступов
    return f"Назначить доступы для пользователя {user_id}"


@bp.route('/map/')
def map():
    wialon = db.session.query(CashWialon).all()
    cesar = db.session.query(CashCesar).all()

    return render_template('map.html', cesar=cesar, wialon=wialon)


