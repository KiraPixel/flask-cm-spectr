import io
import tempfile

from sqlalchemy import func

from app.models import Transport, CashCesar, CashWialon
from . import my_time, location_module, coord_math
from app import db
from modules import mail_sender


def filegen(args):

    output = io.StringIO()

    if 'wialon' in args:
        if args == 'wialon':
            output.write('wialon_id,uNumber,uid,last_time,last_pos_time,x,y' + '\n')
            query = CashWialon.query.all()
            for row in query:
                final_str = (
                    f'{row.id},'
                    f'{row.nm},'
                    f'{row.uid},'
                    f'{my_time.unix_to_moscow_time(row.last_time)},'
                    f'{my_time.unix_to_moscow_time(row.last_pos_time)},'
                    f'{row.pos_x},{row.pos_y}'
                )
                output.write(final_str + '\n')
        elif args == 'wialon_with_address':
            output.write('wialon_id,uNumber,uid,last_time,last_pos_time,address' + '\n')
            query = CashWialon.query.all()
            for row in query:
                location = f"{location_module.get_address(row.pos_y, row.pos_x)}"
                location = location.replace(',', '')
                final_str = (
                    f'{row.id},'
                    f'{row.nm},'
                    f'{row.uid},'
                    f'{my_time.unix_to_moscow_time(row.last_time)},'
                    f'{my_time.unix_to_moscow_time(row.last_pos_time)},'
                    f'{location}'
                )
                output.write(final_str + '\n')
        elif args == 'wialon_offline':
            output.write('wialon_id,uNumber,uid,last_time,last_pos_time,x,y' + '\n')
            query = CashWialon.query.filter(CashWialon.last_time < my_time.get_time_minus_three_days()).all()
            for row in query:
                final_str = (
                    f'{row.id},'
                    f'{row.nm},'
                    f'{row.uid},'
                    f'{my_time.unix_to_moscow_time(row.last_time)},'
                    f'{my_time.unix_to_moscow_time(row.last_pos_time)},'
                    f'{row.pos_x},{row.pos_y}'
                )
                output.write(final_str + '\n')
        else:
            return None
    elif 'cesar' in args:
        output.write('cesar_id,uNumber,PIN,created,last_online,x,y' + '\n')
        if args == 'cesar':
            query = CashCesar.query.all()
            for row in query:
                final_str = (
                    f'{row.unit_id},'
                    f'{row.object_name},'
                    f'{row.pin},'
                    f'{my_time.unix_to_moscow_time(row.created_at)},'
                    f'{my_time.unix_to_moscow_time(row.last_time)},'
                    f'{row.pos_x},{row.pos_y}'
                )

                output.write(final_str + '\n')
        elif args == 'cesar_offline':
            query = CashCesar.query.filter(CashCesar.last_time < my_time.get_time_minus_three_days()).all()
            for row in query:
                final_str = (
                    f'{row.unit_id},'
                    f'{row.object_name},'
                    f'{row.pin},'
                    f'{my_time.unix_to_moscow_time(row.created_at)},'
                    f'{my_time.unix_to_moscow_time(row.last_time)},'
                    f'{row.pos_x},{row.pos_y}'
                )

                output.write(final_str + '\n')
        else:
            return None
    elif 'health' in args:
        if args == 'health_coordinates':
            output.write('Номер лота,Название в Wialon,Дистанция до офиса' + '\n')
            query = db.session.query(Transport, CashWialon). \
                join(CashWialon, CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))). \
                filter(Transport.x != 0). \
                all()
            for transport, cash_wialon in query:
                wialon_pos = (cash_wialon.pos_y, cash_wialon.pos_x)

                work_pos = (transport.x, transport.y)
                if cash_wialon.pos_y == 0:
                    final_str = f'{transport.uNumber},{cash_wialon.nm},None'
                else:
                    delta = coord_math.calculate_distance(wialon_pos, work_pos)
                    final_str = f'{transport.uNumber},{cash_wialon.nm},{delta}'
                output.write(final_str + '\n')
        elif args == 'health_no_equip':
            output.write('uNumber,Кол-во wialon,Кол-во цезерей' + '\n')
            transports = Transport.query.all()
            for transport in transports:
                cesar_count = CashCesar.query.filter(
                    CashCesar.object_name.ilike(f'%{transport.uNumber}%')
                ).count()
                wialon_count = CashWialon.query.filter(
                    CashWialon.nm.ilike(f'%{transport.uNumber}%')
                ).count()
                final_str = f'{transport.uNumber},{wialon_count},{cesar_count}'
                output.write(final_str + '\n')
        elif args == 'health_no_lot':
            output.write('Тип,Имя в системе' + '\n')
            # Получаем все номера транспортных средств
            transport_numbers = {t.uNumber for t in Transport.query.all()}

            # Проверяем оборудование в CashCesar
            for cesar in CashCesar.query.all():
                if not any(transport_number in cesar.object_name for transport_number in transport_numbers):
                    final_str = f'Cesar,{cesar.object_name}'  # Здесь None, так как нет прямого соответствия
                    output.write(final_str + '\n')

            # Проверяем оборудование в CashWialon
            for wialon in CashWialon.query.all():
                if not any(transport_number in wialon.nm for transport_number in transport_numbers):
                    final_str = f'Wialon,{wialon.nm}'  # Здесь None, так как нет прямого соответствия
                    output.write(final_str + '\n')
        else:
            return None
    else:
        return None

    output.seek(0)
    return output.getvalue()


def generate_and_send_report(args, user):
    # Генерация отчёта
    report_content = filegen(args)

    # Если отчёт не сгенерирован, возвращаем ошибку
    if report_content is None:
        return False

    # Письмо
    subject = f'Отчет: {args}'
    body = f'Во вложении заказанный отчет {args}.'

    # Генерируем csv
    attachment_name = f'{args}.csv'
    bom = '\ufeff'
    report_content_with_bom = bom + report_content

    # Отправка отчёта по email
    success = mail_sender.send_email(user.email, subject, body, attachment_name, report_content_with_bom.encode('utf-8'))
    return success
