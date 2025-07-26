from app.models import SystemLog, db
from modules import my_time


def add_log(uNumber, username, prefix, message):
    new_log = SystemLog(date=my_time.now_unix_time(), uNumber=uNumber, username=username, prefix=prefix,
                        message=message)
    db.session.add(new_log)
    db.session.commit()