import os
import threading
import time
from datetime import datetime
from app import create_app

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    if os.getenv('DEV', 0) == 1:
        app.debug = True
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    app.run(host=HOST, port=PORT)
