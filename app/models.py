from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Boolean, text
from sqlalchemy.sql import text

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    status = Column(Integer, default=1)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(50), nullable=False)
    role = Column(Integer, nullable=False)
    last_activity = Column(DateTime, nullable=False, default='1999-12-02 00:00:00')
    first_login = Column(DateTime, nullable=True, default='1999-12-02 00:00:00')
    password_activated_date = Column(DateTime, nullable=True, default='1999-12-02 00:00:00')
    email = Column(String, nullable=False)
    transport_access = Column(JSON)
    functionality_roles = Column(JSON)
    api_token = Column(String, nullable=True)

    def __repr__(self):
        return '<User %r>' % self.username

class Reports(db.Model):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), primary_key=True)
    type = Column(String(100), nullable=True)
    status = Column(String(100), nullable=True)
    start_date = Column(Integer)
    updated_date = Column(Integer)
    end_date = Column(Integer)
    parameters = Column(JSON)
    percentage_completed = Column(Float)
    success = Column(Boolean, nullable=False,    default=False)
    errors = Column(String, nullable=True)

class Transport(db.Model):
    __tablename__ = 'transport'

    id = Column(Integer, primary_key=True)
    storage_id = Column(Integer, ForeignKey('storage.ID'), nullable=False)
    model_id = Column(Text, ForeignKey('transport_model.id'), nullable=False)
    storage = db.relationship('Storage', back_populates='transports', primaryjoin="Storage.ID == Transport.storage_id")
    uNumber = Column(Text)
    manufacture_year = Column(Text)
    vin = Column(Text)
    x = Column(Float)
    y = Column(Float)
    customer = Column(Text)
    customer_contact = Column(Text)
    manager = Column(Text)
    alert_preset = Column(Integer)
    alert_preset_updated_date = Column(Integer)
    parser_1c = Column(Integer, default=1)
    jamming_risk = Column(Text(15), default='low')

    transport_model = db.relationship(
        'TransportModel',
        back_populates='transports',
        primaryjoin="Transport.model_id == TransportModel.id"
    )

    def __repr__(self):
        return '<Transport %r>' % self.uNumber

class Storage(db.Model):
    __tablename__ = 'storage'

    ID = Column(Integer, primary_key=True)
    name = Column(String(100))
    type = Column(String(100))
    region = Column(String(100))
    address = Column(String(100))
    organization = Column(String(100))
    transports = db.relationship('Transport', back_populates='storage',
                                 primaryjoin="Storage.ID == Transport.storage_id")

    def __repr__(self):
        return '<Storage %r>' % self.name

class TransportModel(db.Model):
    __tablename__ = 'transport_model'

    id = Column(Text, primary_key=True)
    type = Column(String(100))
    name = Column(String(100))
    lift_type = Column(String(100))
    engine = Column(String(100))
    country = Column(String(100))
    machine_type = Column(String(100))
    brand = Column(String(100))
    model = Column(String(100))
    transports = db.relationship('Transport', back_populates='transport_model',
                                 primaryjoin="Transport.model_id == TransportModel.id")

    def __repr__(self):
        return '<TransportModel %r>' % self.name

class CashCesar(db.Model):
    __tablename__ = 'cash_cesar'
    unit_id = Column(Integer, primary_key=True, index=True)
    object_name = Column(Text, nullable=False)
    pin = Column(Integer, default=0)
    vin = Column(Text, nullable=False)
    last_time = Column(Integer, default=0)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    created_at = Column(Integer, default=0)
    device_type = Column(Text, nullable=False)
    linked = Column(Boolean, nullable=True, default=False)  # TINYINT(1) NULL DEFAULT '0'

class CashAxenta(db.Model):
    __tablename__ = 'cash_axenta'
    id = Column(Integer, primary_key=True)
    uid = Column(Integer, nullable=False, default=0)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    gps = Column(Integer, default=0)
    last_time = Column(Integer, default=0)
    last_pos_time = Column(Integer, default=0)
    connected_status = Column(Boolean, nullable=True, default=False)
    cmd = Column(Text, nullable=True, default='')
    sens = Column(Text, nullable=True, default='')
    valid_nav = Column(Integer, nullable=True, default=1)
    engine_hours = Column(Float, default=0.0)

class CashHistoryWialon(db.Model):
    __tablename__ = 'cash_history_wialon'
    id = Column(Integer, primary_key=True)
    uid = Column(Integer, nullable=False, default=0)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    last_time = Column(Integer, default=0)
    valid_nav = Column(Integer, default=1)
    engine_hours = Column(Float, default=0.0)

class CashHistoryCesar(db.Model):
    __tablename__ = 'cash_history_cesar'
    id = Column(Integer, primary_key=True)
    pin = Column(Text, nullable=False, default=0)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    last_time = Column(Integer, default=0)

class CashHistoryAxenta(db.Model):
    __tablename__ = 'cash_history_axenta'
    id = Column(Integer, primary_key=True)
    uid = Column(Integer, nullable=False, default=0)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    last_time = Column(Integer, default=0)
    valid_nav = Column(Integer, nullable=True, default=0)
    engine_hours = Column(Float, default=0.0)

class Alert(db.Model):
    __tablename__ = 'alert'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Integer, nullable=False, default=0)
    uNumber = Column(Text(50), nullable=False)
    type = Column(Text(50), db.ForeignKey('alert_type.alert_un'), nullable=False)
    data = Column(Text(50), nullable=False)
    status = Column(Integer, nullable=True, default=0)
    comment = Column(String(100), nullable=True)
    comment_editor = Column(String(100), nullable=True)
    date_time_edit = Column(Integer, nullable=False, default=0)

    alert_type = db.relationship('AlertType', backref='alerts')


class AlertType(db.Model):
    __tablename__ = 'alert_type'
    alert_un = Column(String(255), primary_key=True, nullable=False)
    localization = Column(Text, nullable=False)
    criticality = Column(Text)
    category = Column(Text, nullable=False)


class AlertTypePresets(db.Model):
    __tablename__ = 'alerts_type_presets'
    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    preset_name = Column(Text, nullable=False)
    enable_alert_types = Column(Text)
    disable_alert_types = Column(Text)
    wialon_danger_distance = Column(Integer, default=5)
    wialon_danger_hours_not_work = Column(Integer, default=72)
    active = Column(Integer, nullable=False, default=1)
    editable = Column(Integer, nullable=False, default=1)
    personalized = Column(Integer, nullable=False, default=0)


class Coord(db.Model):
    __tablename__ = 'coord_cash'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    address = Column(String(100), nullable=True)
    updated_time = Column(Integer, nullable=False, default=0)


class Comments(db.Model):
    __tablename__ = 'comments'
    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    author = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    uNumber = Column(Text, nullable=False)
    datetime_unix = Column(Integer, nullable=True, default=0)


class IgnoredStorage(db.Model):
    __tablename__ = 'ignored_storage'
    id = Column(Integer, primary_key=True)
    named = Column(Text, nullable=False)
    pos_x = Column(Float, nullable=False)
    pos_y = Column(Float, nullable=False)
    radius = Column(Integer, nullable=False)
    address = Column(Text, nullable=True)


class ParserTasks(db.Model):
    __tablename__ = 'tasks_parser'

    id = Column(Integer, primary_key=True)
    task_name = Column(String(100))
    info = Column(String(100))
    variable = Column(String(100))
    task_completed = Column(Integer, default=0)
    task_manager = Column(String(100))


class TransferTasks(db.Model):
    __tablename__ = 'tasks_transport_transfer'

    id = Column(Integer, primary_key=True)
    uNumber = Column(String(100))
    old_storage = Column(Integer())
    new_storage = Column(Integer())
    old_manager = Column(String(100))
    new_manager = Column(String(100))
    old_client = Column(String(100))
    new_client = Column(String(100))
    date = Column(Integer())


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = Column(Integer, primary_key=True)
    enable_voperator = Column(Integer)
    enable_xml_parser = Column(Integer)
    enable_db_cashing = Column(Integer)


class FunctionalityAccess(db.Model):
    __tablename__ = 'user_functionality_access'
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    localization = Column(String(100))
    category = Column(String(100))
    category_localization = Column(String(100))


class SystemLog(db.Model):
    __tablename__ = 'system_log'
    id = Column(Integer, primary_key=True)
    date = Column(String(100))
    uNumber = Column(String(100))
    username = Column(String(100))
    prefix = Column(String(100))
    message = Column(String(100))


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
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error inserting mailing record: {e}")
        return False


def reports_custom_transport_transfer(start_date, end_date, region, home_storage):
    try:
        sql = text("""
            CALL cm.reports_custom_transport_transfer(
            :start_date, 
            :end_date, 
            :region, 
            :home_storage)
        """)

        result = db.session.execute(sql, {
            'start_date': start_date,
            'end_date': end_date,
            'region': f'%{region}%',
            'home_storage': home_storage
        })

        rows = result.fetchall()
        result.close()
        db.session.commit()

        columns = ['номер_лота', 'склад', 'регион', 'тип', 'модель_техники',
                    'дата_перемещения', 'виалон_количество', 'виалон_онлайн', 'цезарь_количество', 'пресет_ид', 'пресет_имя']
        result_list = [dict(zip(columns, row)) for row in rows]

        return result_list
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при вызове процедуры custom_transport_transfer: {e}")
        return False

