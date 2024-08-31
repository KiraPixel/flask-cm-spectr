from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from .utils import login_required
from .models import db, User
from modules import hash_password

us_bp = Blueprint('user_settings', __name__)


@us_bp.route('/')
@login_required
def index():
    user = User.query.filter_by(username=session['username']).first_or_404()
    return(render_template('pages/user_settings/page.html', user=user))


@us_bp.route('/email', methods=['GET', 'POST'])
@login_required
def change_email():
    if request.method == 'POST':
        new_email = request.form.get('email')
        user = User.query.filter_by(username=session['username']).first_or_404()
        user.email = new_email
        db.session.commit()
        flash('Email успешно изменен.', 'success')
        return redirect(url_for('user_settings.index'))

    return render_template('pages/user_settings/email.html')


@us_bp.route('/pass', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        new_password = hash_password.hash_password(new_password)

        user = User.query.filter_by(username=session['username']).first_or_404()
        user.password = new_password
        db.session.commit()
        flash('Пароль успешно изменен.', 'success')
        return redirect(url_for('user_settings.index'))

    return render_template('pages/user_settings/pass.html')