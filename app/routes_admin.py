import xml.etree.ElementTree as ET
from flask import Blueprint, request, render_template, redirect, url_for, flash, g, session
from .utils import need_access, need_access
from .models import db, User, Transport, IgnoredStorage, Storage, ParserTasks
from modules import mail_sender, hash_password


admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
def set_user():
    g.user = User.query.filter_by(username=session['username']).first()


@admin_bp.route('/', methods=['GET', 'POST'])
@need_access(1)
def admin_panel():
    if request.method == 'POST':
        if 'username' in request.form:
            # Логика для добавления пользователя
            username = request.form['username']
            email = request.form['email']
            password = hash_password.generator_password()
            h_password = hash_password.hash_password(password)
            new_user = User(username=username, email=email, password=h_password, role=-1,
                            last_activity="1999-12-02 00:00:00", access_managers="[]", access_regions="[]")
            db.session.add(new_user)
            db.session.commit()
            body = render_template('standalone/mail_new_user.html', user=new_user, password=password)
            mail_sender.send_email(new_user.email, "Приглашение в Центр Мониторинга ЛК-СПЕКТР", body)
            return redirect(url_for('admin.admin_panel'))

        elif 'name' in request.form:
            # Логика для добавления склада
            name = request.form['name']
            # Заменяем запятую на точку в координатах
            pos_x = request.form['x_coord'].replace(',', '.')
            pos_y = request.form['y_coord'].replace(',', '.')
            radius = request.form['radius']

            # Конвертируем строки в числа для корректного сохранения в БД
            pos_x = float(pos_x)
            pos_y = float(pos_y)
            radius = int(radius)

            new_storage = IgnoredStorage(named=name, pos_x=pos_x, pos_y=pos_y, radius=radius)
            db.session.add(new_storage)
            db.session.commit()
            return redirect(url_for('admin.admin_panel'))

    users = User.query.all()
    ignored_storages = IgnoredStorage.query.all()
    return render_template('pages/admin_panel/page.html', users=users, ignored_storages=ignored_storages)


@admin_bp.route('/parser')
@need_access(1)
def parser_page():
    tasks_with_error_all = ParserTasks.query.filter(
        ParserTasks.task_completed == 0,
        ~ParserTasks.task_name.in_(['new_car', 'new_car_error'])
    ).all()
    tasks_with_error_new_car = ParserTasks.query.filter(
        ParserTasks.task_completed == 0,
        ParserTasks.task_name.in_(['new_car', 'new_car_error'])
    ).all()

    parsed_tasks = []  # Массив для хранения обработанных данных

    for task in tasks_with_error_new_car:
        if not task.info:
            print(f"Пустое содержимое task.info для задачи ID {task.id}")
            parsed_tasks.append({"id": task.id, "error": "Пустое содержимое XML"})
            continue

        try:
            root = ET.fromstring(task.info)  # assuming 'info' содержит XML

            task_data = {
                "id": task.id,  # Добавляем ID задачи для привязки
                "код_склада": root.attrib.get("КодСклада", "").strip() or "None",
                "склад": root.attrib.get("Склад", "").strip() or "None",
                "лот": root.attrib.get("Лот", "").strip() or "None",
                "ИДМодели": root.attrib.get("ИДМодели", "").strip() or "None",
                "серия": root.attrib.get("Серия", "").strip() or "None",
                "серия_год_выпуска": root.attrib.get("СерияГодВыпуска", "").strip() or "None",
                "широта": root.attrib.get("Широта", "").strip() or "None",
                "долгота": root.attrib.get("Долгота", "").strip() or "None",
                "контрагент": root.attrib.get("Контрагент", "").strip() or "None",
                "менеджер": root.attrib.get("ОтветственныйМенеджер", "").strip() or "None"
            }

            parsed_tasks.append(task_data)

        except Exception as e:
            print(f"Ошибка при обработке XML для задачи ID {task.id}: {e}")
            parsed_tasks.append({"id": task.id, "error": f"Ошибка при обработке XML: {e}"})

    # Возвращаем шаблон с задачами с ошибками и обработанными данными
    return render_template('pages/parser/page.html', tasks_with_error=tasks_with_error_all, parsed_tasks=parsed_tasks)


@admin_bp.route('/delete_storage/<int:storage_id>', methods=['POST'])
@need_access(1)
def delete_storage(storage_id):
    storage = IgnoredStorage.query.get_or_404(storage_id)
    db.session.delete(storage)
    db.session.commit()
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/set_cesar_access/<int:user_id>', methods=['GET'])
@need_access(1)
def set_cesar_access(user_id):
    user = User.query.get_or_404(user_id)

    # Получаем значение параметра 'access'
    access = request.args.get('access', type=int)

    # Проверяем корректность значения access
    if access not in [0, 1]:
        flash('Недопустимое значение для доступа.', 'error')
        return redirect(url_for('admin.admin_panel'))

    # Устанавливаем доступ
    user.cesar_access = access

    # Сохраняем изменения в базе данных
    db.session.commit()

    flash(f'Доступ для {user.username} к системе Цезарь был изменен.', 'success')
    return redirect(url_for('admin.admin_panel'))


# Редактирование пользователя
@admin_bp.route('/edit_user/<int:user_id>', methods=['POST'])
@need_access(1)
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
@need_access(1)
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален.', 'success')
    return redirect(url_for('admin.admin_panel'))


# Назначение доступов пользователю
@admin_bp.route('/set_access/<int:user_id>', methods=['GET', 'POST'])
@need_access(1)
def set_access(user_id):
    user = User.query.get_or_404(user_id)

    # Получаем уникальных менеджеров и регионы
    unique_customers = db.session.query(Transport.manager).distinct().all()
    unique_regions = db.session.query(Storage.region).distinct().all()

    # Преобразуем в список
    managers = [manager[0] for manager in unique_customers]
    regions = [region[0] for region in unique_regions]

    if request.method == 'POST':
        access_managers = request.form.get('access_managers')
        access_regions = request.form.get('access_regions')

        # Сохраняем доступы
        user.access_managers = access_managers
        user.access_regions = access_regions
        db.session.commit()

        flash('Доступы обновлены', 'success')
        return redirect(url_for('admin.admin_panel'))

    return render_template('pages/admin_panel/set_access.html', user=user, managers=managers, regions=regions)


# Функция для обновления пароля пользователя
def update_user_password(user_id, new_password):
    user = User.query.get_or_404(user_id)
    new_password = hash_password.hash_password(new_password)
    user.password = new_password
    db.session.commit()


# Изменить пароль
@admin_bp.route('/change_pass/<int:user_id>/<string:password>')
@need_access(1)
def change_pass(user_id, password):
    update_user_password(user_id, password)

    return redirect(url_for('admin.admin_panel'))


# Сброс пароля
@admin_bp.route('/reset_pass/<int:user_id>')
@need_access(1)
def reset_pass(user_id):
    user = User.query.get_or_404(user_id)

    new_password = hash_password.generator_password()
    update_user_password(user_id, new_password)

    body = render_template('standalone/mail_info.html', password=new_password)
    mail_sender.send_email(user.email, "Новый временный пароль для вашего аккаунта в ЛК-СПЕКТР", body)

    flash(f'Пароль пользователя {user.username} успешно сброшен.', 'success')
    return redirect(url_for('admin.admin_panel'))



