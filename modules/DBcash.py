from custom_api.cesar import CesarConnector
from custom_api.wialon import WialonSearcher
from sqlalchemy import create_engine, Column, Integer, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import time

# Замените на ваш реальный URL базы данных
SQLALCHEMY_DATABASE_URL = ""

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CashCesar(Base):
    __tablename__ = 'cash_cesar'
    unit_id = Column(Integer, primary_key=True, index=True)
    object_name = Column(Text, nullable=False)
    pin = Column(Integer, default=0)
    vin = Column(Text, nullable=False)
    lasti_time = Column(Integer, default=0)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    created_at = Column(Integer, default=0)
    device_type = Column(Text, nullable=False)

class CashWialon(Base):
    __tablename__ = 'cash_wialon'
    id = Column(Integer, primary_key=True, index=True)
    nm = Column(Text, nullable=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    last_time = Column(Integer, default=0)

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

def to_unix_time(dt_str):
    if dt_str is None:
        return 0
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return int(time.mktime(dt.timetuple()))

def ClearDB():
    session = SessionLocal()
    try:
        session.query(CashCesar).delete()
        session.query(CashWialon).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error occurred while clearing the database: {e}")
    finally:
        session.close()

def UpdateDB():
    session = SessionLocal()
    try:
        Cesar = CesarConnector.CesarApi()
        cesar_result = Cesar.get_cars_info()
        wialon_result = WialonSearcher.search_all_items(originals=True)

        for item in cesar_result:
            unit_id = item['unit_id']
            object_name = item['object_name']
            pin = item['pin']
            vin = item['vin']
            lasti_time = to_unix_time(item.get('receive_time'))
            pos_x = item['lat']
            pos_y = item['lon']
            created_at = to_unix_time(item.get('created_at'))
            device_type = item['device_type'] if item['device_type'] is not None else 'Unknown'

            cesar_entry = CashCesar(
                unit_id=unit_id,
                object_name=object_name,
                pin=pin,
                vin=vin,
                lasti_time=lasti_time,
                pos_x=pos_x,
                pos_y=pos_y,
                created_at=created_at,
                device_type=device_type
            )
            session.add(cesar_entry)

        for item in wialon_result:
            nm = item['nm']
            id = item['id']
            pos = item['pos']

            pos_x = pos['x'] if pos else 0.0
            pos_y = pos['y'] if pos else 0.0
            last_time = pos['t'] if pos else 0

            wialon_entry = CashWialon(
                id=id,
                nm=nm,
                pos_x=pos_x,
                pos_y=pos_y,
                last_time=last_time
            )
            session.add(wialon_entry)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error occurred: {e}")
    finally:
        session.close()

# Сначала очищаем таблицы, затем обновляем данные
ClearDB()
UpdateDB()
