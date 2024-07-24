import io

from flask import send_file

from custom_api.wialon import WialonSearcher
from custom_api.cesar import CesarConnector
from app.models import db, CashCesar, CashWialon
from . import MyTime


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
            #нужно будет переделать
            for row in WialonSearcher.search_all_items(address=True):
                output.write(row + '\n')
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
    else:
        return None

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'{args}.txt'
    )