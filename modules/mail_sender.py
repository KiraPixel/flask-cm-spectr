import os
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody

sender_email = os.getenv('MAIL_MAIL', 'nomail@nomail')
sender_login = os.getenv('MAIL_USERNAME', 'user')
sender_password = os.getenv('MAIL_PASSWORD', 'password')


def send_email(target_email, subject, body):
    try:
        # Создаем учетные данные
        credentials = Credentials(username=sender_login, password=sender_password)

        # Подключаемся к учетной записи
        account = Account(sender_email, credentials=credentials, autodiscover=True, access_type=DELEGATE)

        # Создаем сообщение
        msg = Message(
            account=account,
            folder=account.sent,
            subject=subject,
            body=HTMLBody(body),
            to_recipients=[target_email]
        )

        # Отправляем сообщение
        msg.send()
        return True
    except Exception as e:
        return False


