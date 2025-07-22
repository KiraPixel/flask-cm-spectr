from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Integer, nullable=False)
    last_activity = db.Column(db.DateTime, nullable=False, default='1999-12-02 00:00:00')
    first_login = db.Column(db.DateTime, nullable=True, default='1999-12-02 00:00:00')
    password_activated_date = db.Column(db.DateTime, nullable=True, default='1999-12-02 00:00:00')
    email = db.Column(db.String, nullable=False)
    transport_access = db.Column(db.JSON)
    functionality_roles = db.Column(db.JSON)
    cesar_access = db.Column(db.Integer, nullable=True, default=0)
    api_token = db.Column(db.String, nullable=True)

    def __repr__(self):
        return '<User %r>' % self.username


class Reports(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), primary_key=True)
    type = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(100), nullable=True)


class Transport(db.Model):
    __tablename__ = 'transport'

    id = db.Column(db.Integer, primary_key=True)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.ID'), nullable=False)
    model_id = db.Column(db.Text, db.ForeignKey('transport_model.id'), nullable=False)  # Указание внешнего ключа
    storage = db.relationship('Storage', back_populates='transports', primaryjoin="Storage.ID == Transport.storage_id")
    uNumber = db.Column(db.Text)
    manufacture_year = db.Column(db.Text)
    vin = db.Column(db.Text)
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    customer = db.Column(db.Text)
    customer_contact = db.Column(db.Text)
    manager = db.Column(db.Text)
    alert_preset = db.Column(db.Integer)
    parser_1c = db.Column(db.Integer, default=1)

    transport_model = db.relationship(
        'TransportModel',
        back_populates='transports',
        primaryjoin="Transport.model_id == TransportModel.id"
    )

    def __repr__(self):
        return '<Transport %r>' % self.uNumber


class Storage(db.Model):
    __tablename__ = 'storage'

    ID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(100))
    region = db.Column(db.String(100))
    address = db.Column(db.String(100))
    organization = db.Column(db.String(100))
    transports = db.relationship('Transport', back_populates='storage',
                                 primaryjoin="Storage.ID == Transport.storage_id")

    def __repr__(self):
        return '<Storage %r>' % self.name


class TransportModel(db.Model):
    __tablename__ = 'transport_model'

    id = db.Column(db.Text, primary_key=True)
    type = db.Column(db.String(100))
    name = db.Column(db.String(100))
    lift_type = db.Column(db.String(100))
    engine = db.Column(db.String(100))
    country = db.Column(db.String(100))
    machine_type = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    transports = db.relationship('Transport', back_populates='transport_model',
                                 primaryjoin="Transport.model_id == TransportModel.id")

    def __repr__(self):
        return '<TransportModel %r>' % self.name


class CashCesar(db.Model):
    __tablename__ = 'cash_cesar'
    unit_id = db.Column(db.Integer, primary_key=True, index=True)
    object_name = db.Column(db.Text, nullable=False)
    pin = db.Column(db.Integer, default=0)
    vin = db.Column(db.Text, nullable=False)
    last_time = db.Column(db.Integer, default=0)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.Integer, default=0)
    device_type = db.Column(db.Text, nullable=False)
    linked = db.Column(db.Boolean, nullable=True, default=False)  # TINYINT(1) NULL DEFAULT '0'


class CashWialon(db.Model):
    __tablename__ = 'cash_wialon'
    id = db.Column(db.Integer, primary_key=True, index=True)
    uid = db.Column(db.Integer, nullable=False, default=0)
    nm = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    gps = db.Column(db.Integer, default=0)
    last_time = db.Column(db.Integer, default=0)
    last_pos_time = db.Column(db.Integer, default=0)
    linked = db.Column(db.Boolean, nullable=True, default=False)  # TINYINT(1) NULL DEFAULT '0'
    cmd = db.Column(db.Text, nullable=True, default='')
    sens = db.Column(db.Text, nullable=True, default='')


class CashHistoryWialon(db.Model):
    __tablename__ = 'cash_history_wialon'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, nullable=False, default=0)
    nm = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    last_time = db.Column(db.Integer, default=0)


class CashHistoryCesar(db.Model):
    __tablename__ = 'cash_history_cesar'
    id = db.Column(db.Integer, primary_key=True)
    pin = db.Column(db.Text, nullable=False, default=0)
    nm = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    last_time = db.Column(db.Integer, default=0)


class Alert(db.Model):
    __tablename__ = 'alert'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Integer, nullable=False, default=0)
    uNumber = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(255), db.ForeignKey('alert_type.alert_un'), nullable=False)  # Изменяем на String(255) и добавляем ForeignKey
    data = db.Column(db.Text, nullable=False)
    status = db.Column(db.Integer, nullable=True, default=0)
    comment = db.Column(db.String(100), nullable=True)
    comment_editor = db.Column(db.String(100), nullable=True)
    date_time_edit = db.Column(db.Integer, nullable=False, default=0)

    alert_type = db.relationship('AlertType', backref='alerts')


class AlertType(db.Model):
    __tablename__ = 'alert_type'
    alert_un = db.Column(db.String(255), primary_key=True, nullable=False)
    localization = db.Column(db.Text, nullable=False)
    criticality = db.Column(db.Text)
    category = db.Column(db.Text, nullable=False)


class AlertTypePresets(db.Model):
    __tablename__ = 'alerts_type_presets'
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    preset_name = db.Column(db.Text, nullable=False)
    enable_alert_types = db.Column(db.Text)
    disable_alert_types = db.Column(db.Text)
    wialon_danger_distance = db.Column(db.Integer, default=5)
    wialon_danger_hours_not_work = db.Column(db.Integer, default=72)
    active = db.Column(db.Integer, nullable=False, default=1)
    editable = db.Column(db.Integer, nullable=False, default=1)
    personalized = db.Column(db.Integer, nullable=False, default=0)


class Coord(db.Model):
    __tablename__ = 'coord_cash'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    address = db.Column(db.String(100), nullable=True)
    updated_time = db.Column(db.Integer, nullable=False, default=0)


class Comments(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    uNumber = db.Column(db.Text, nullable=False)
    datetime_unix = db.Column(db.Integer, nullable=True, default=0)


class IgnoredStorage(db.Model):
    __tablename__ = 'ignored_storage'
    id = db.Column(db.Integer, primary_key=True)
    named = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Float, nullable=False)
    pos_y = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Integer, nullable=False)
    address = db.Column(db.Text, nullable=True)


class ParserTasks(db.Model):
    __tablename__ = 'tasks_parser'

    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100))
    info = db.Column(db.String(100))
    variable = db.Column(db.String(100))
    task_completed = db.Column(db.Integer, default=0)
    task_manager = db.Column(db.String(100))


class TransferTasks(db.Model):
    __tablename__ = 'tasks_transport_transfer'

    id = db.Column(db.Integer, primary_key=True)
    uNumber = db.Column(db.String(100))
    old_storage = db.Column(db.Integer())
    new_storage = db.Column(db.Integer())
    old_manager = db.Column(db.String(100))
    new_manager = db.Column(db.String(100))
    old_client = db.Column(db.String(100))
    new_client = db.Column(db.String(100))
    date = db.Column(db.Integer())


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    enable_voperator = db.Column(db.Integer)
    enable_xml_parser = db.Column(db.Integer)
    enable_db_cashing = db.Column(db.Integer)


class FunctionalityAccess(db.Model):
    __tablename__ = 'user_functionality_access'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    localization = db.Column(db.String(100))
    category = db.Column(db.String(100))
    category_localization = db.Column(db.String(100))


def insert_mailing_record_sqlalchemy(target, subject, content, html_template=None, attachment_name=None, attachment_content=None):
    try:
        sql = text("""
            CALL insert_mailing_record(
                :target,
                :subject,
                :content,
                :html_template,
                :attachment_name,
                :attachment_content
            )
        """)
        db.session.execute(sql, {
            'target': target,
            'subject': subject,
            'content': content,
            'html_template': html_template,
            'attachment_name': attachment_name,
            'attachment_content': attachment_content
        })
        db.session.commit()
        return True  # Успешное выполнение
    except Exception as e:
        db.session.rollback()
        print(f"Error inserting mailing record: {e}")
        return False