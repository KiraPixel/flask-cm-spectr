import os
import io
from datetime import timedelta, datetime
import time
import json
from functools import wraps
import re

from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

from custom_api.wialon import WialonSearcher
from custom_api.cesar import CesarConnector
from custom_api.jira import jirasearcher
from geopy.geocoders import Nominatim


app = Flask(__name__)

with open('config.json', 'r') as f:
    config = json.load(f)

with open('config_jira.json', 'r') as f:
    jira_config = json.load(f)

app.secret_key = config['SECRET_KEY']
app.debug = True
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
# Настройка подключения к базе данных
app.config['SQLALCHEMY_DATABASE_URI'] = config['SQLALCHEMY_DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
geolocator = Nominatim(user_agent="KiraPixel")
Jira = jirasearcher.JiraConnector(jira_config['url'], jira_config['username'], jira_config['password'])

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Integer, nullable=False)
    last_activity = db.Column(db.DateTime, nullable=False)
    email = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


class Transport(db.Model):
    __tablename__ = 'transport'

    id = db.Column(db.Integer, primary_key=True)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.ID'), nullable=False)
    uNumber = db.Column(db.String(10))
    model = db.Column(db.String(100))

    storage = db.relationship('Storage', back_populates='transports', primaryjoin="Transport.storage_id == Storage.ID")

    def __repr__(self):
        return '<Transport %r>' % self.uNumber


class Storage(db.Model):
    __tablename__ = 'storage'

    ID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(100))
    region = db.Column(db.String(100))
    address = db.Column(db.String(100))
    organization = db.Column(db.String(100))

    transports = db.relationship('Transport', back_populates='storage', primaryjoin="Storage.ID == Transport.storage_id")


    def __repr__(self):
        return '<Storage %r>' % self.uNumber


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        else:
            user = User.query.filter_by(username=session['username']).first_or_404()
            user.last_activity = datetime.now()
            db.session.commit()
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(username=session['username']).first_or_404()
        if user.role != 1:
            flash('Нет прав', 'warning')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def home():
    columns = ['№ Лота', 'Модель', 'Склад', 'Регион']  # Заголовки столбцов
    columns_data = []
    filter_time = False
    session = db.session

    nm = request.args.get('nm')

    last_time_start = request.args.get('last_time_start')
    last_time_end = request.args.get('last_time_end')
    data = []

    if nm is not None and nm != '':
        for transport, storage in db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).filter(Transport.uNumber.like(f'%{nm}%')).all():

            columns_data.append([transport.uNumber, transport.model, storage.name, storage.region, ])
    elif last_time_start or last_time_end:
        last_time_start_unix = None
        last_time_end_unix = None
        if last_time_start:
            try:
                last_time_start_unix = time.mktime(datetime.strptime(last_time_start, '%Y-%m-%dT%H:%M').timetuple())
            except ValueError:
                pass
        if last_time_end:
            try:
                last_time_end_unix = time.mktime(datetime.strptime(last_time_end, '%Y-%m-%dT%H:%M').timetuple())
            except ValueError:
                pass
        data = WialonSearcher.search_all_items(last_time_start_unix=last_time_start_unix,last_time_end_unix=last_time_end_unix)
        for transport, storage in db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).all():
            if any(x.startswith(transport.uNumber) for x in data):
                columns_data.append([transport.uNumber, transport.model, storage.name, storage.region, ])
    else:
        for transport, storage in db.session.query(Transport, Storage).join(Storage, Transport.storage_id == Storage.ID).all():

            columns_data.append([transport.uNumber, transport.model, storage.name, storage.region, ])




    return render_template('filter.html', columns=columns, table_rows=columns_data, redi='/cars/', request=request)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session.permanent = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = 'Неправильный логин или пароль. Попробуйте снова.'
    return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/rep')
@login_required
def reports():
    return render_template('reports.html')


@app.route('/cars/<string:car_id>')
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
    Car = WialonSearcher.search_item(car_id)
    if Car is not None:
        Car.convert_all()

    jira_info = Jira.search(search_pattern)
    return render_template('car.html', car_name=car_id, Car=Car, jira=jira_info)


@app.route('/download')
@login_required
def download():
    report_name = request.args.get('report')
    if report_name == "wialon":
        # Создаем текстовый файл "на лету"
        output = io.StringIO()
        for row in WialonSearcher.search_all_items():
            output.write(row + '\n')
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='wialon_report.txt'
        )
    if report_name == "wialon_with_address":
        output = io.StringIO()
        for row in WialonSearcher.search_all_items(address=True):
            output.write(row + '\n')
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='wialon_offline_report.txt'
        )
    if report_name == "wialon_offline":
        output = io.StringIO()
        for row in WialonSearcher.search_all_items(True):
            output.write(row + '\n')
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='wialon_offline_report.txt'
        )
    if report_name == "cesar":
        # Создаем текстовый файл "на лету"
        output = io.StringIO()
        Cesar = CesarConnector.CesarApi()
        for row in Cesar.get_cars_info(toString=True):
            output.write(row + '\n')
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='cesar_report.txt'
        )
    if report_name == "cesar_offline":
        # Создаем текстовый файл "на лету"
        output = io.StringIO()
        Cesar = CesarConnector.CesarApi()
        for row in Cesar.get_cars_info(toString=True, offline=True):
            output.write(row + '\n')
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/plain',
            as_attachment=True,
            download_name='cesar_report.txt'
        )


@app.route('/admin/', methods=['GET', 'POST'])
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
        return redirect(url_for('admin_panel'))

    users = User.query.all()
    return render_template('admin_panel.html', users=users)


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        return redirect(url_for('admin_panel'))

    return render_template('edit_user.html', user=user)


@app.route('/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/set_access/<int:user_id>')
@login_required
@admin_required
def set_access(user_id):
    user = User.query.get_or_404(user_id)
    # Логика назначения доступов
    return f"Назначить доступы для пользователя {user_id}"


app.run(host=config['HOST'])