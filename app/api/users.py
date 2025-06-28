from symtable import Class

import bleach
from flask import request, jsonify, session
from flask_restx import Namespace, Resource, fields

from app.models import Comments, db, Alert
from app.utils import need_access
from modules.my_time import now_unix_time

user_ns = Namespace('users', description='user staff')

add_comment_parser = user_ns.parser()
add_comment_parser.add_argument('text', type=str, required=True, help='Текст комментария', location='form')
add_comment_parser.add_argument('uNumber', type=str, required=True, help='Уникальный номер авто', location='form')

@user_ns.route('/add_comment')
class AddComment(Resource):
    @user_ns.expect(add_comment_parser)
    @need_access(-1)
    def post(self):
        text = request.form.get('text', '').strip()
        uNumber = request.form.get('uNumber')
        author = session.get('username')
        print(text, uNumber, author)
        if not text or not uNumber or not author:
            return jsonify({'status': 'comment_deny'})

        clean_text = bleach.clean(text, strip=True)
        if len(clean_text) > 500 or len(clean_text) <= 1:
            return jsonify({'status': 'comment_deny'})

        new_comment = Comments(author=author, text=clean_text, uNumber=uNumber, datetime_unix=now_unix_time())
        db.session.add(new_comment)
        db.session.commit()

        return jsonify({'status': 'comment_ok'})


edit_comment_parser = user_ns.parser()
edit_comment_parser.add_argument('comment_id', type=int, required=True, location='form')
edit_comment_parser.add_argument('text', type=str, required=False, help='Текст комментария', location='form')
edit_comment_parser.add_argument('action', type=str, required=False, help='Передать delete для удаления', location='form')

@user_ns.route('/edit_comment')
class EditComment(Resource):
    @user_ns.expect(edit_comment_parser)
    @need_access(-1)
    def post(self):
        comment_id = request.form.get('comment_id')
        action = request.form.get('action')
        author = session.get('username')
        text = request.form.get('text', '').strip()

        if not comment_id or not author:
            return jsonify({'status': 'edit_deny'})

        # Находим комментарий по ID и проверяем, что автор совпадает
        comment = Comments.query.get(comment_id)
        if not comment or comment.author != author:
            return jsonify({'status': 'edit_deny'})

        # Если действие "удалить", обновляем uNumber
        if action == 'delete':
            comment.uNumber = f"{comment.uNumber}_removed"
            db.session.commit()
            return jsonify({'status': 'edit_ok'})

        # Для редактирования текста
        if not text or len(text) > 500:
            return jsonify({'status': 'edit_deny'})

        comment.text = text
        db.session.commit()

        return jsonify({'status': 'edit_ok'})

edit_comment_model = user_ns.model('EditAlertComment', {
    'comment_id': fields.String(required=True, description='ID алерта'),
    'comment': fields.String(required=True, description='Текст комментария')
})

@user_ns.route('/edit_alert_comment')
class EditAlertComment(Resource):
    @user_ns.expect(edit_comment_model, validate=True)
    @need_access(-1)
    def post(self):
        data = request.json
        report_id = data.get('comment_id')
        new_comment = data.get('comment')
        author = session.get('username')

        if not report_id or not author:
            return jsonify({'status': 'edit_deny'})

        report = Alert.query.get(report_id)

        # Для редактирования текста
        text = new_comment.strip()
        if not text or len(text) > 500:
            return jsonify({'status': 'edit_deny'})

        report.comment = text
        report.comment_editor = author
        report.date_time_edit = now_unix_time()
        db.session.commit()

        return jsonify({'status': 'edit_ok'})