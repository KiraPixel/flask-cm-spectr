from operator import and_

import bleach
from flask import request, jsonify, session
from flask_restx import Namespace, Resource, fields
from ..models import Comments, db, Alert, User
from ..utils import need_access
from modules import hash_password
from modules.my_time import now_unix_time

user_ns = Namespace('users', description='Операции с пользователями')

# Парсер для добавления комментария
add_comment_parser = user_ns.parser()
add_comment_parser.add_argument('text', type=str, required=True, help='Текст комментария (максимум 500 символов)', location='form')
add_comment_parser.add_argument('uNumber', type=str, required=True, help='Уникальный номер автомобиля', location='form')

# Парсер для редактирования комментария
edit_comment_parser = user_ns.parser()
edit_comment_parser.add_argument('comment_id', type=int, required=True, help='ID комментария', location='form')
edit_comment_parser.add_argument('text', type=str, required=False, help='Текст комментария (максимум 500 символов)', location='form')
edit_comment_parser.add_argument('action', type=str, required=False, help='Действие: "delete" для удаления комментария', location='form')

# Парсер для редактирования комментария к алерту
edit_comment_model = user_ns.model('EditAlertComment', {
    'comment_id': fields.Integer(required=True, description='ID алерта'),
    'comment': fields.String(required=True, description='Текст комментария (максимум 500 символов)')
}, description='Данные для редактирования комментария к алерту')

# Парсер для смены пароля
change_pass_parser = user_ns.parser()
change_pass_parser.add_argument('password', type=str, required=True, help='Новый пароль пользователя', location='form')


# Добавление комментария
@user_ns.route('/add_comment')
class AddComment(Resource):
    @user_ns.expect(add_comment_parser)
    @need_access('car_comments')
    def post(self):
        """Добавить новый комментарий к автомобилю"""
        text = request.form.get('text', '').strip()
        uNumber = request.form.get('uNumber')
        author = session.get('username')
        if not text or not uNumber or not author:
            return jsonify({'status': 'comment_deny'})

        clean_text = bleach.clean(text, strip=True)
        if len(clean_text) > 500 or len(clean_text) <= 1:
            return jsonify({'status': 'comment_deny'})

        new_comment = Comments(author=author, text=clean_text, uNumber=uNumber, datetime_unix=now_unix_time())
        db.session.add(new_comment)
        db.session.commit()

        return jsonify({'status': 'comment_ok'})

# Редактирование или удаление комментария
@user_ns.route('/edit_comment')
class EditComment(Resource):
    @user_ns.expect(edit_comment_parser)
    @need_access('car_comments')
    def post(self):
        """Редактировать или удалить существующий комментарий"""
        comment_id = request.form.get('comment_id')
        action = request.form.get('action')
        author = session.get('username')
        text = request.form.get('text', '').strip()

        if not comment_id or not author:
            return jsonify({'status': 'edit_deny'})

        comment = Comments.query.get(comment_id)
        if not comment or comment.author != author:
            return jsonify({'status': 'edit_deny'})

        if action == 'delete':
            comment.uNumber = f"{comment.uNumber}_removed"
            db.session.commit()
            return jsonify({'status': 'edit_ok'})

        if not text or len(text) > 500:
            return jsonify({'status': 'edit_deny'})

        comment.text = text
        db.session.commit()

        return jsonify({'status': 'edit_ok'})

# Редактирование комментария к алерту
@user_ns.route('/edit_alert_comment')
class EditAlertComment(Resource):
    @user_ns.expect(edit_comment_model, validate=True)
    @need_access('voperator')
    def post(self):
        """Редактировать комментарий к алерту"""
        data = request.json
        report_id = data.get('comment_id')
        new_comment = data.get('comment')
        author = session.get('username')

        if not report_id or not author:
            return jsonify({'status': 'edit_deny'})

        report = Alert.query.get(report_id)

        text = new_comment.strip()
        if not text or len(text) > 500:
            return jsonify({'status': 'edit_deny'})

        report.comment = text
        report.comment_editor = author
        report.date_time_edit = now_unix_time()
        db.session.commit()

        return jsonify({'status': 'edit_ok'})

# Смена пароля текущим пользователем
@user_ns.route('/change_pass')
class ChangePass(Resource):
    @user_ns.expect(change_pass_parser)
    @need_access('login')
    def put(self):
        """Сменить пароль текущего пользователя"""
        args = change_pass_parser.parse_args()
        password = args['password']
        user = User.query.filter_by(username=session['username']).first_or_404()
        user.password = hash_password.hash_password(password)
        db.session.commit()
        return {'status': 'password_changed'}, 200
