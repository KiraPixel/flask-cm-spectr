from datetime import datetime
import time
import re
import io

from flask import Blueprint, render_template, request, send_file, redirect, url_for, session, flash

from . import Jira
from .models import db, User, Transport, Storage, CashWialon, CashCesar
from .utils import login_required, admin_required
from .modules import ReportGenerator
from custom_api.wialon import WialonSearcher
from custom_api.cesar import CesarConnector
from custom_api.jira import jirasearcher




bp = Blueprint('main', __name__)


@bp.route('/', endpoint='home')
@login_required
def home():
    columns = ['№ Лота', 'Модель', 'Склад', 'Регион']  # Заголовки столбцов
    columns_data = []
    data_db = None
    ts_bd = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID)

    filter_nm = request.args.get('nm')
    filter_last_time_start = request.args.get('last_time_start')
    filter_last_time_end = request.args.get('last_time_end')
    filet_model = request.args.get('model')
    filter_storage = request.args.get('storage')
    filter_region = request.args.get('region')

    if filter_nm:
        data_db = ts_bd.filter(Transport.uNumber.like(f'%{filter_nm}%')).all()
    elif filet_model:
        data_db = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).filter(
            Transport.model.like(f'%{filet_model}%')).all()
    elif filter_storage:
        data_db = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).filter(
            Storage.name.like(f'%{filter_storage}%')).all()
    elif filter_region:
        data_db = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).filter(
            Storage.region.like(f'%{filter_region}%')).all()
    else:
        data_db = db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).all()

    if filter_last_time_start or filter_last_time_end:
        last_time_start_unix = None
        last_time_end_unix = None
        if filter_last_time_start:
            try:
                last_time_start_unix = time.mktime(datetime.strptime(filter_last_time_start, '%Y-%m-%dT%H:%M').timetuple())
            except ValueError:
                pass
        if filter_last_time_end:
            try:
                last_time_end_unix = time.mktime(datetime.strptime(filter_last_time_end, '%Y-%m-%dT%H:%M').timetuple())
            except ValueError:
                pass
        data = WialonSearcher.search_all_items(last_time_start_unix=last_time_start_unix,last_time_end_unix=last_time_end_unix)
        for transport, storage in data_db:
            if any(x.startswith(transport.uNumber) for x in data):
                columns_data.append([transport.uNumber, transport.model, storage.name, storage.region, ])
    else:
        for transport, storage in data_db:
            columns_data.append([transport.uNumber, transport.model, storage.name, storage.region, ])



    return render_template('filter.html', columns=columns, table_rows=columns_data, redi='/cars/', request=request)


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


@bp.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


@bp.route('/rep')
@login_required
def reports():
    return render_template('reports.html')


@bp.route('/cars/<string:car_id>')
@login_required
def get_car(car_id):
    text = car_id.replace(' ', '')
    if re.match(r'^[A-Z]+\d{5}$', text):
        # Добавляем пробел перед цифрами, если его нет
        if text[1] != ' ':
            car_id = text[:1] + ' ' + text[1:]
    search_pattern = f'%{car_id}%'
    results = Transport.query.filter(Transport.uNumber.like(search_pattern)).first()
    #print(results.uNumber)
    wialon = WialonSearcher.search_item(car_id)
    cesar = ''
    if wialon is not None:
        wialon.convert_all()


    jira_info = Jira.search(search_pattern)
    return render_template('car.html', car_name=car_id, cesar=cesar, wialon=wialon, jira=jira_info)


@bp.route('/download', endpoint="download")
@login_required
def download():
    report_name = request.args.get('report')
    return ReportGenerator.filegen(report_name)

@bp.route('/admin/', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_panel():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        new_user = User(username=username, email=email, password=password, role=role, last_activity="1999-12-02 00:00:00")
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main.admin_panel'))

    users = User.query.all()
    return render_template('admin_panel.html', users=users)


@bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        return redirect(url_for('main.admin_panel'))

    return render_template('edit_user.html', user=user)


@bp.route('/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('main.admin_panel'))


@bp.route('/set_access/<int:user_id>')
@login_required
@admin_required
def set_access(user_id):
    user = User.query.get_or_404(user_id)
    # Логика назначения доступов
    return f"Назначить доступы для пользователя {user_id}"