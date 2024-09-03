from functools import wraps
from flask import session, flash, redirect, url_for, render_template
from .models import db, User
from modules import my_time
import datetime


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Вы пытались зайти на страницу к которой требуется авторизация.', 'warning')
            return redirect(url_for('main.login'))
        else:
            msk_time = datetime.datetime.fromtimestamp(my_time.now_unix_time(), tz=datetime.timezone(datetime.timedelta(hours=3)))
            user = User.query.filter_by(username=session['username']).first_or_404()
            user.last_activity = msk_time.strftime('%Y-%m-%d %H:%M')

            db.session.commit()
        return f(*args, **kwargs)

    return decorated_function


def need_access(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Вы пытались зайти на страницу к которой требуется авторизация.', 'warning')
                return redirect(url_for('main.login'))
            user = User.query.filter_by(username=session['username']).first_or_404()
            if user.role < required_role:
                flash('Недостаточно прав для доступа', 'warning')
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
