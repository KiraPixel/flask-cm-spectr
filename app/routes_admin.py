import secrets
import string

from flask import Blueprint, request, render_template, redirect, url_for, flash
from .utils import login_required, admin_required
from .models import db, User
from modules import mail_sender, hash_password


admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_panel():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password.generator_password()
        h_password = hash_password.hash_password(password)
        new_user = User(username=username, email=email, password=h_password, role=0,
                        last_activity="1999-12-02 00:00:00")
        db.session.add(new_user)
        db.session.commit()

        body = render_template('standalone/mail_new_user.html', user=new_user, password=password)
        mail_sender.send_email(new_user.email, "Приглашение в Центр Мониторинга ЛК-СПЕКТР", body)
        return redirect(url_for('admin.admin_panel'))

    users = User.query.all()
    return render_template('pages/admin_panel/page.html', users=users)


# Редактирование пользователя
@admin_bp.route('/edit_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        flash('Пользователь изменен.', 'success')
        return redirect(url_for('admin.admin_panel'))

    return redirect(url_for('admin.admin_panel'))


# Удаление пользователя
@admin_bp.route('/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален.', 'success')
    return redirect(url_for('admin.admin_panel'))


# Назначение доступов пользователю
@admin_bp.route('/set_access/<int:user_id>')
@login_required
@admin_required
def set_access(user_id):
    user = User.query.get_or_404(user_id)
    return f"Назначить доступы для пользователя {user}"


# Функция для обновления пароля пользователя
def update_user_password(user_id, new_password):
    user = User.query.get_or_404(user_id)
    new_password = hash_password.hash_password(new_password)
    user.password = new_password
    db.session.commit()


# Изменить пароль
@admin_bp.route('/change_pass/<int:user_id>/<string:password>')
@login_required
@admin_required
def change_pass(user_id, password):
    update_user_password(user_id, password)

    return redirect(url_for('admin.admin_panel'))


# Сброс пароля
@admin_bp.route('/reset_pass/<int:user_id>')
@login_required
@admin_required
def reset_pass(user_id):
    user = User.query.get_or_404(user_id)
    new_password = hash_password.generator_password()
    update_user_password(user_id, new_password)
    body = render_template('standalone/mail_info.html', password=new_password)
    mail_sender.send_email(user.email, "Новый временный пароль для вашего аккаунта в ЛК-СПЕКТР", body)
    flash('Пароль сброшен.', 'success')
    return redirect(url_for('admin.admin_panel'))



