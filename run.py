import os
import threading
import time
from datetime import datetime
from app import create_app

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    app.debug = True
    app.run(host=os.getenv('HOST', '0.0.0.0'))
