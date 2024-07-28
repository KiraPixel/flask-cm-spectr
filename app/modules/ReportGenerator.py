import io

from flask import send_file
from sqlalchemy import func

from app.models import Transport, CashCesar, CashWialon
from . import MyTime, LocationModule, CoordMath
from app import db
from math import radians, sin, cos, sqrt, atan2

def filegen(args):
    output = io.StringIO()
    if 'wialon' in args:
        if args == 'wialon':
            output.write('wialon_id;uNumber;last_time;last_pos_time;x_y poistion' + '\n')
            query = CashWialon.query.all()
            for row in query:
                final_str = f'{row.id};{row.nm};{MyTime.unix_to_moscow_time(row.last_time)};{MyTime.unix_to_moscow_time(row.last_pos_time)};{row.pos_x},{row.pos_y}'
                output.write(final_str + '\n')
        elif args == 'wialon_with_address':
            output.write('wialon_id;uNumber;last_time;last_pos_time;address' + '\n')
            query = CashWialon.query.all()
            for row in query:
                location = LocationModule.get_address(row.pos_y, row.pos_x)
                final_str = f'{row.id};{row.nm};{MyTime.unix_to_moscow_time(row.last_time)};{MyTime.unix_to_moscow_time(row.last_pos_time)};{location}'
                output.write(final_str + '\n')
        elif args == 'wialon_offline':
            output.write('wialon_id;uNumber;;last_time;last_pos_time;x_y poistion' + '\n')
            query = CashWialon.query.filter(CashWialon.last_time < MyTime.get_time_minus_three_days()).all()
            for row in query:
                final_str = f'{row.id};{row.nm};{MyTime.unix_to_moscow_time(row.last_time)};{MyTime.unix_to_moscow_time(row.last_pos_time)};{row.pos_x},{row.pos_y}'
                output.write(final_str + '\n')
        else:
            return None
    elif 'cesar' in args:
        output.write('cesar_id;uNumber;PIN;created;last_online' + '\n')
        if args == 'cesar':
            query = CashCesar.query.all()
            for row in query:
                final_str = f'{row.unit_id};{row.object_name};{row.pin};{MyTime.unix_to_moscow_time(row.created_at)};{MyTime.unix_to_moscow_time(row.last_time)}'
                output.write(final_str + '\n')
        elif args == 'cesar_offline':
            query = CashCesar.query.filter(CashCesar.last_time < MyTime.get_time_minus_three_days()).all()
            for row in query:
                final_str = f'{row.unit_id};{row.object_name};{row.pin};{MyTime.unix_to_moscow_time(row.created_at)};{MyTime.unix_to_moscow_time(row.last_time)}'
                output.write(final_str + '\n')
        else:
            return None
    elif 'health' in args:
        if args == 'health_coordinates':
            output.write('Номер лота;Название в Wialon;Дистанция до офиса' + '\n')
            query = db.session.query(Transport, CashWialon). \
                join(CashWialon, CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))). \
                all()
            for transport, cash_wialon in query:
                wialon_pos = (cash_wialon.pos_y, cash_wialon.pos_x) #это баг виалона, нужно привнуть или мб однажды поменять
                office_pos = (55.913856, 37.417132)
                if cash_wialon.pos_y == 0:
                    final_str = f'{transport.uNumber};{cash_wialon.nm};None'
                else:
                    delta = CoordMath.calculate_distance(wialon_pos, office_pos)
                    final_str = f'{transport.uNumber};{cash_wialon.nm};{delta}'
                output.write(final_str + '\n')
        elif args == 'health_no_equip':
            output.write('uNumber;Кол-во wialon;Кол-во цезерей' + '\n')
            transports = Transport.query.all()
            for transport in transports:
                cesar_count = CashCesar.query.filter(
                    CashCesar.object_name.ilike(f'%{transport.uNumber}%')
                ).count()
                wialon_count = CashWialon.query.filter(
                    CashWialon.nm.ilike(f'%{transport.uNumber}%')
                ).count()
                final_str = f'{transport.uNumber};{wialon_count};{cesar_count}'
                output.write(final_str + '\n')
        elif args == 'health_no_lot':
            output.write('Тип;Имя в системе' + '\n')
            # Получаем все номера транспортных средств
            transport_numbers = {t.uNumber for t in Transport.query.all()}

            # Проверяем оборудование в CashCesar
            for cesar in CashCesar.query.all():
                if not any(transport_number in cesar.object_name for transport_number in transport_numbers):
                    final_str = f'Wialon;{cesar.object_name}'  # Здесь None, так как нет прямого соответствия
                    output.write(final_str + '\n')

            # Проверяем оборудование в CashWialon
            for wialon in CashWialon.query.all():
                if not any(transport_number in wialon.nm for transport_number in transport_numbers):
                    final_str = f'Cesar;{wialon.nm}'  # Здесь None, так как нет прямого соответствия
                    output.write(final_str + '\n')
        else:
            return None
    else:
        return None

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'{args}.txt'
    )