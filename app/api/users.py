import bleach
from flask import request, jsonify, session, g
from flask_restx import Namespace, Resource, fields
from ..models import Comments, db, Alert, User, Reports
from ..utils import need_access
from modules import hash_password
from modules.my_time import now_unix_time

user_ns = Namespace('users', description='Операции с пользователями')

add_comment_parser = user_ns.parser()
add_comment_parser.add_argument('text', type=str, required=True, help='Текст комментария (максимум 500 символов)', location='form')
add_comment_parser.add_argument('uNumber', type=str, required=True, help='Уникальный номер автомобиля', location='form')

edit_comment_parser = user_ns.parser()
edit_comment_parser.add_argument('comment_id', type=int, required=True, help='ID комментария', location='form')
edit_comment_parser.add_argument('text', type=str, required=False, help='Текст комментария (максимум 500 символов)', location='form')
edit_comment_parser.add_argument('action', type=str, required=False, help='Действие: "delete" для удаления комментария', location='form')

edit_comment_model = user_ns.model('EditAlertComment', {
    'comment_id': fields.String(required=True, description='ID алерта'),
    'comment': fields.String(required=True, description='Текст комментария (максимум 500 символов)')
}, description='Данные для редактирования комментария к алерту')

change_pass_parser = user_ns.parser()
change_pass_parser.add_argument('password', type=str, required=True, help='Новый пароль пользователя', location='form')

user_me_model = user_ns.model('UserMe', {
    'id': fields.Integer(readonly=True, description='ID пользователя'),
    'username': fields.String(readonly=True, description='Логин'),
    'email': fields.String(readonly=True, description='Email'),
    'status': fields.Integer(readonly=True, description='Статус аккаунта'),
    'role': fields.Integer(readonly=True, description='Роль пользователя'),
    'last_activity': fields.DateTime(readonly=True, description='Последняя активность'),
    'first_login': fields.DateTime(readonly=True, description='Первый вход'),
    'password_activated_date': fields.DateTime(readonly=True, description='Дата активации пароля'),
    'transport_access': fields.Raw(readonly=True, description='Доступ к транспорту (JSON)'),
    'functionality_roles': fields.Raw(readonly=True, description='Функциональные роли (JSON)'),
})

change_email_model = user_ns.model('ChangeEmailRequest', {
    'email': fields.String(required=True, description='Новый email', min_length=6)
})

change_email_response = user_ns.model('ChangeEmailResponse', {
    'status': fields.String,
    'message': fields.String
})

report_model = user_ns.model('UserReport', {
    'id': fields.Integer(readonly=True, description='ID отчёта'),
    'type': fields.String(readonly=True, description='Тип отчёта'),
    'status': fields.String(readonly=True, description='Статус'),
    'start_date': fields.Integer(readonly=True, description='Дата начала (unix)'),
    'updated_date': fields.Integer(readonly=True, description='Дата последнего обновления (unix)'),
    'end_date': fields.Integer(readonly=True, description='Дата завершения (unix)'),
    'percentage_completed': fields.Float(readonly=True, description='Процент выполнения'),
    'success': fields.Boolean(readonly=True, description='Успешно завершён'),
    'errors': fields.String(readonly=True, description='Ошибки (если есть)'),
    'parameters': fields.Raw(readonly=True, description='Параметры отчёта (JSON)'),
})

reports_list_model = user_ns.model('UserReportsList', {
    'status': fields.String(default='success'),
    'count': fields.Integer(description='Количество отчётов'),
    'reports': fields.List(fields.Nested(report_model), description='Список отчётов пользователя')
})

@user_ns.route('/add_comment')
class AddComment(Resource):
    @user_ns.expect(add_comment_parser)
    @need_access('car_comments')
    def post(self):
        text = request.form.get('text', '').strip()
        uNumber = request.form.get('uNumber')
        author = g.user.username
        if not text or not uNumber or not author:
            return jsonify({'status': 'comment_deny'})

        clean_text = bleach.clean(text, strip=True)
        if len(clean_text) > 500 or len(clean_text) <= 1:
            return jsonify({'status': 'comment_deny'})

        new_comment = Comments(author=author, text=clean_text, uNumber=uNumber, datetime_unix=now_unix_time())
        db.session.add(new_comment)
        db.session.commit()

        return jsonify({'status': 'comment_ok'})

@user_ns.route('/edit_comment')
class EditComment(Resource):
    @user_ns.expect(edit_comment_parser)
    @need_access('car_comments')
    def post(self):
        comment_id = request.form.get('comment_id')
        action = request.form.get('action')
        author = g.user.username
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

@user_ns.route('/edit_alert_comment')
class EditAlertComment(Resource):
    @user_ns.expect(edit_comment_model, validate=True)
    @need_access('voperator')
    def post(self):
        data = request.json
        report_id = data.get('comment_id')
        new_comment = data.get('comment')
        author = g.user.username

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

@user_ns.route('/me/password')
class ChangeMyPassword(Resource):
    @user_ns.expect(change_pass_parser)
    @need_access('login')
    def put(self):
        args = change_pass_parser.parse_args()
        new_password = args['password']

        if len(new_password) < 6:
            return {'status': 'error', 'message': 'Пароль слишком короткий'}, 400

        g.user.password = hash_password.hash_password(new_password)
        db.session.commit()

        return {'status': 'success', 'message': 'Пароль успешно изменён'}, 200

@user_ns.route('/me')
class CurrentUser(Resource):
    @user_ns.marshal_with(user_me_model)
    @need_access('login')
    def get(self):
        user = g.user

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'status': user.status,
            'role': user.role,
            'last_activity': user.last_activity,
            'first_login': user.first_login,
            'password_activated_date': user.password_activated_date,
            'transport_access': user.transport_access,
            'functionality_roles': user.functionality_roles,
        }, 200

@user_ns.route('/me/email')
class ChangeMyEmail(Resource):
    @user_ns.expect(change_email_model, validate=True)
    @user_ns.marshal_with(change_email_response)
    @need_access('login')
    def put(self):
        data = user_ns.payload
        new_email = data['email'].strip().lower()

        if "@" not in new_email or len(new_email) < 6:
            return {'status': 'error', 'message': 'Некорректный формат email'}, 400

        existing = User.query.filter(
            User.email == new_email,
            User.id != g.user.id
        ).first()

        if existing:
            return {'status': 'error', 'message': 'Этот email уже используется'}, 409

        g.user.email = new_email
        db.session.commit()

        return {'status': 'success', 'message': 'Email успешно изменён'}, 200

@user_ns.route('/me/reports')
class UserReports(Resource):
    @user_ns.marshal_with(reports_list_model)
    @need_access('login')
    def get(self):
        """Получить все отчёты текущего пользователя"""
        current_username = g.user.username

        reports = Reports.query.filter_by(username=current_username)\
                              .order_by(Reports.start_date.desc())\
                              .all()

        result = []
        for rep in reports:
            result.append({
                'id': rep.id,
                'type': rep.type,
                'status': rep.status,
                'start_date': rep.start_date,
                'updated_date': rep.updated_date,
                'end_date': rep.end_date,
                'percentage_completed': rep.percentage_completed,
                'success': rep.success,
                'errors': rep.errors,
                'parameters': rep.parameters,
            })

        return {
            'status': 'success',
            'count': len(result),
            'reports': result
        }, 200