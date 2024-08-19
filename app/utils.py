from functools import wraps
from flask import session, flash, redirect, url_for, render_template
from .models import db, User
from .modules import MyTime
import time
import datetime

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Вы пытались зайти на страницу к которой требуется авторизация.', 'warning')
            return redirect(url_for('main.login'))
        else:
            msk_time = datetime.datetime.fromtimestamp(MyTime.now_unix_time(), tz=datetime.timezone(datetime.timedelta(hours=3)))
            user = User.query.filter_by(username=session['username']).first_or_404()
            user.last_activity = msk_time.strftime('%Y-%m-%d %H:%M')

            db.session.commit()
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(username=session['username']).first_or_404()
        if user.role != 1:
            return render_template('error.html', error_message='Нет прав')
        return f(*args, **kwargs)

    return decorated_function
