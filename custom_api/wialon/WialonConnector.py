import datetime
from wialon import Wialon, WialonError, flags
from geopy.geocoders import Nominatim
from app import config

geolocator = Nominatim(user_agent="KiraPixel")
token = config.WIALON_TOKEN

class Car:
    def __init__(self):
        self.id = None
        self.nm = None
        self.uuid = None
        self.last_time_msg = None
        self.last_pos_msg = None

        self.last_x_pos = None
        self.last_y_pos = None
        self.sputniks = None
        self.last_time = None
        self.yandex_maps_url = None
        self.address = None

    def convert_all(self):
        self.convert_pos_msg()
        self.convert_time_msg()

    def convert_time_msg(self):
        if self.last_time_msg is not None:
            self.last_time = convert_to_moscow_time(self.last_time_msg['t'])
            return True
        return False

    def convert_pos_msg(self):
        if self.last_pos_msg is not None:
            self.last_y_pos = self.last_pos_msg['y']
            self.last_x_pos = self.last_pos_msg['x']
            self.sputniks = self.last_pos_msg['sc']
            return True
        return False

    def refresh_address(self):
        if self.convert_pos_msg():
            location = geolocator.reverse((self.last_y_pos, self.last_x_pos), exactly_one=True)
            self.yandex_maps_url = f"https://yandex.ru/maps/?ll={self.last_x_pos}%2C{self.last_y_pos}&z=14&pt={self.last_x_pos},{self.last_y_pos},pm2rdm"
            self.address = location.address
            return True
        return False


def wialon_connector():
    # Создание экземпляра Wialon
    wialon_api = Wialon()
    # Авторизация с использованием токена
    result = wialon_api.token_login(token='7e134b2935ca593e81c9f3a6f21065eaC1C6AB50D35C56768D6610345E6D04F875BCBB62')
    # Установка ID сессии
    wialon_api.sid = result['eid']
    return wialon_api


def convert_to_moscow_time(timestamp):
    # Перевод метки времени в объект datetime с временной зоной UTC
    dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

    # Установка часового пояса МСК (UTC+3)
    moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))
    dt_msk = dt_utc.astimezone(moscow_timezone)

    # Форматирование даты и времени
    formatted_time = dt_msk.strftime('%d-%m-%Y %H:%M:%S')
    return formatted_time
