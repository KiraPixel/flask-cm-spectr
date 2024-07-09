import os
import io
from datetime import timedelta, datetime
import json
from functools import wraps
import re

from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

from custom_api.wialon import WialonSearcher
from custom_api.cesar import CesarConnector
from geopy.geocoders import Nominatim


app = Flask(__name__)

with open('config.json', 'r') as f:
    config = json.load(f)

app.secret_key = config['SECRET_KEY']
app.debug = False
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "false"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
# Настройка подключения к базе данных
app.config['SQLALCHEMY_DATABASE_URI'] = config['SQLALCHEMY_DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
geolocator = Nominatim(user_agent="KiraPixel")


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
    region = db.Column(db.String(100))
    storage = db.Column(db.String(100))
    uNumber = db.Column(db.String(10))
    model = db.Column(db.String(100))

    def __repr__(self):
        return '<Transport %r>' % self.uNumber


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
    columns = ['№ Лота', 'Регион', 'Склад', 'Модель']  # Заголовки столбцов
    test_data = []
    session = db.session
    for item in session.query(Transport).all():
        test_data.append([item.uNumber, item.region, item.storage, item.model])
    return render_template('filter.html', columns=columns, table_rows=test_data, redi='/cars/')


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
    Car.convert_all()
    return render_template('test2.html', Car=Car)


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