from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from .utils import need_access
from .models import db, User, Reports
from modules import hash_password

us_bp = Blueprint('user_profile', __name__)


@us_bp.route('/')
@need_access(-2)
def index():
    user = User.query.filter_by(username=session['username']).first_or_404()
    reports = Reports.query.filter_by(username=session['username']).order_by(Reports.id.desc()).all()
    return(render_template('pages/user_profile/page.html', user=user, reports=reports))


@us_bp.route('/email', methods=['GET', 'POST'])
@need_access(-2)
def change_email():
    if request.method == 'POST':
        new_email = request.form.get('email')
        user = User.query.filter_by(username=session['username']).first_or_404()
        user.email = new_email
        db.session.commit()
        flash('Email успешно изменен.', 'success')
        return redirect(url_for('user_profile.index'))

    return render_template('pages/user_profile/email.html')


@us_bp.route('/pass', methods=['GET', 'POST'])
@need_access(-2)
def change_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        new_password = hash_password.hash_password(new_password)

        user = User.query.filter_by(username=session['username']).first_or_404()
        user.password = new_password
        db.session.commit()
        flash('Пароль успешно изменен.', 'success')
        return redirect(url_for('user_profile.index'))

    return render_template('pages/user_profile/pass.html')