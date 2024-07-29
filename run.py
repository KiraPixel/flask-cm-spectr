import os
import threading
import time
from datetime import datetime
from app import create_app
from app.modules import DBcash

def update_db_periodically():
    while True:
        start_time = time.time()  # Сохраняем время начала обновления
        print(f"DB UPDATE | {datetime.now()} Thread {threading.current_thread().name} is updating DB...")
        DBcash.UpdateBD()
        print(f"DB UPDATE | {datetime.now()} END")
        end_time = time.time()  # Сохраняем время окончания обновления
        duration = end_time - start_time  # Вычисляем длительность обновления
        print(f"DB UPDATE | {datetime.now()} Update duration: {duration:.2f} seconds")
        # Если обновление занимает меньше времени, чем интервал, ждем оставшееся время
        sleep_time = max(80 - duration, 0)
        time.sleep(sleep_time)


# Создаем приложение
app = create_app()


if __name__ == '__main__':
    if not any(t.name == 'UpdateDBThread' and t.is_alive() for t in threading.enumerate()):
        update_thread = threading.Thread(target=update_db_periodically, name='UpdateDBThread')
        update_thread.daemon = True
        update_thread.start()
    app.debug = True
    app.run(host=os.getenv('HOST', '0.0.0.0'))
