import os
from app import create_app

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    if os.getenv('DEV', 0) == '1':
        app.debug = True
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '31500'))
    app.run(host=HOST, port=PORT)
