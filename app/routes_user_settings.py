import logging

from flask import Blueprint, request, render_template, redirect, url_for, session, flash, g
from .utils import need_access
from .models import db, User, Reports
from modules import hash_password

# Создаем Blueprint
us_bp = Blueprint('user_profile', __name__)
# Описываем основной логгер
logger = logging.getLogger('flask_cm_spectr')

@us_bp.before_request
def before_request():
    logger.debug(
        'Request: User=%s, Method=%s, URL=%s',
        g.user, request.method, request.url,
    )


@us_bp.route('/')
@need_access('login')
def index():
    user = g.user
    reports = Reports.query.filter_by(username=user.username).order_by(Reports.id.desc()).all()
    return(render_template('pages/user_profile/page.html', user=user, reports=reports))


@us_bp.route('/email', methods=['GET', 'POST'])
@need_access('login')
def change_email():
    if request.method == 'POST':
        new_email = request.form.get('email')
        user = g.user
        user.email = new_email
        db.session.commit()
        flash('Email успешно изменен.', 'success')
        return redirect(url_for('user_profile.index'))

    return render_template('pages/user_profile/email.html')


@us_bp.route('/pass', methods=['GET', 'POST'])
@need_access('login')
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        new_password = hash_password.hash_password(new_password)

        user = g.user
        user.password = new_password
        db.session.commit()
        flash('Пароль успешно изменен.', 'success')
        return redirect(url_for('user_profile.index'))

    return render_template('pages/user_profile/pass.html')