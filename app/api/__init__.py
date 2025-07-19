from flask import Blueprint
from flask_restx import Api

# Создаем основной Blueprint
api_bp = Blueprint('api', __name__)

# Инициализация API с поддержкой авторизации
api = Api(api_bp,
          version='1.0',
          title='API Documentation',
          description='Описание и документация для API',
          authorizations={
              'api_key': {
                  'type': 'apiKey',
                  'in': 'header',
                  'name': 'X-API-KEY'
              }
          },
          security='api_key')

# Импорт маршрутов для регистрации Namespace (будет заполнено позже)
from .health import health_ns
from .car import car_ns
from .api_key import api_key_ns
from .users import user_ns
from .wialon import wialon_ns
from .parser import parser_ns
from .setting import settings_ns
from .alerts_presets import alerts_presets_ns
from .admin import admin_ns, admin_users_ns, admin_storages_ns

# Добавление Namespace в API
api.add_namespace(health_ns)
api.add_namespace(car_ns)
api.add_namespace(api_key_ns)
api.add_namespace(user_ns)
api.add_namespace(wialon_ns)
api.add_namespace(parser_ns)
api.add_namespace(settings_ns)
api.add_namespace(alerts_presets_ns)
api.add_namespace(admin_ns)
api.add_namespace(admin_users_ns)
api.add_namespace(admin_storages_ns)