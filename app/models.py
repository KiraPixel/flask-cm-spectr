from . import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Integer, nullable=False)
    last_activity = db.Column(db.DateTime, nullable=False)
    email = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username


class Transport(db.Model):
    __tablename__ = 'transport'

    id = db.Column(db.Integer, primary_key=True)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.ID'), nullable=False)
    uNumber = db.Column(db.String(10))
    model = db.Column(db.String(100))

    storage = db.relationship('Storage', back_populates='transports', primaryjoin="Transport.storage_id == Storage.ID")

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

    transports = db.relationship('Transport', back_populates='storage', primaryjoin="Storage.ID == Transport.storage_id")


    def __repr__(self):
        return '<Storage %r>' % self.uNumber


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


class CashWialon(db.Model):
    __tablename__ = 'cash_wialon'
    id = db.Column(db.Integer, primary_key=True, index=True)
    nm = db.Column(db.Text, nullable=False)
    pos_x = db.Column(db.Float, default=0.0)
    pos_y = db.Column(db.Float, default=0.0)
    last_time = db.Column(db.Integer, default=0)
