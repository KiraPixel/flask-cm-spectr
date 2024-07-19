import threading
import time
from app import create_app
from app.modules import DBcash

def update_db_periodically():
    while True:
        DBcash.UpdateBD()
        time.sleep(60)  # ждем 60 секунд


# Создаем и запускаем поток для обновления БД
update_thread = threading.Thread(target=update_db_periodically)
update_thread.daemon = True  # делаем поток демоном, чтобы он завершался при завершении основного потока
update_thread.start()

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
