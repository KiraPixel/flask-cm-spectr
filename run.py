import logging
import os
from app import create_app

# Настройка логгера
logger = logging.getLogger('flask_cm_spectr')
logger.setLevel(logging.DEBUG)

# Отключаем шум от Werkzeug и urllib3
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Только ошибки
logging.getLogger('urllib3').setLevel(logging.WARNING)  # Только предупреждения

# Настраиваем обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.handlers = [console_handler]  # Только консоль

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    if os.getenv('DEV', '0') == '1':
        logger.debug('Запуск в режиме разработки (DEBUG=True)')
        app.debug = True
    else:
        logger.debug('Запуск в режиме продакшена')

    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '31500'))
    logger.info('Запуск сервера: host=%s, port=%d', HOST, PORT)
    app.run(host=HOST, port=PORT)