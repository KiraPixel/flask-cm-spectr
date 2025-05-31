import os
from exchangelib import Credentials, Account, Message, DELEGATE, HTMLBody, FileAttachment

sender_email = os.getenv('MAIL_MAIL', 'nomail@nomail')
sender_login = os.getenv('MAIL_USERNAME', 'user')
sender_password = os.getenv('MAIL_PASSWORD', 'password')


def send_email(target_email, subject, body, attachment_name=None, attachment_content=None):
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
        print(f'Send email to {target_email} with subject "{subject}" from "{sender_email}" login {sender_login}')
        if attachment_name:
            attachment = FileAttachment(
                name=attachment_name,
                content=attachment_content,
            )
            msg.attach(attachment)

        # Отправляем сообщение
        msg.send()
        return True
    except Exception as e:
        print(e)
        return False


