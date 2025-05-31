import io
import tempfile
import time

from sqlalchemy import func
from openpyxl import Workbook
from app.models import Transport, CashCesar, CashWialon, Reports, Alert, TransportModel, Storage
from app.utils import get_address_from_coords
from . import my_time, location_module, coord_math
from app import db
from modules import mail_sender

def filegen(args):
    wb = Workbook()
    ws = wb.active

    if 'wialon' in args:
        if args == 'wialon':
            ws.append(['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'x', 'y'])
            query = CashWialon.query.all()
            for row in query:
                ws.append([
                    row.id,
                    row.nm,
                    row.uid,
                    my_time.unix_to_moscow_time(row.last_time),
                    my_time.unix_to_moscow_time(row.last_pos_time),
                    row.pos_x,
                    row.pos_y
                ])
        elif args == 'wialon_with_address':
            ws.append(['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'address'])
            query = CashWialon.query.all()
            for row in query:
                location = None
                max_attempts = 50
                for attempt in range(max_attempts):
                    try:
                        location = get_address_from_coords(row.pos_y, row.pos_x)
                        location = str(location)
                        if location != "Time out to convert":
                            break
                    except Exception as e:
                        print(f"Попытка {attempt + 1} из {max_attempts} не удалась: {e}")

                    if attempt < max_attempts - 1:
                        time.sleep(5)
                    if not location or location == "Time out to convert":
                        location = "Unable to retrieve address"
                ws.append([
                    row.id,
                    row.nm,
                    row.uid,
                    my_time.unix_to_moscow_time(row.last_time),
                    my_time.unix_to_moscow_time(row.last_pos_time),
                    location
                ])
        elif args == 'wialon_offline':
            ws.append(['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'x', 'y'])
            query = CashWialon.query.filter(CashWialon.last_time < my_time.get_time_minus_three_days()).all()
            for row in query:
                ws.append([
                    row.id,
                    row.nm,
                    row.uid,
                    my_time.unix_to_moscow_time(row.last_time),
                    my_time.unix_to_moscow_time(row.last_pos_time),
                    row.pos_x,
                    row.pos_y
                ])
        else:
            return None
    elif 'cesar' in args:
        ws.append(['cesar_id', 'uNumber', 'PIN', 'created', 'last_online', 'x', 'y'])
        if args == 'cesar':
            query = CashCesar.query.all()
            for row in query:
                ws.append([
                    row.unit_id,
                    row.object_name,
                    row.pin,
                    my_time.unix_to_moscow_time(row.created_at),
                    my_time.unix_to_moscow_time(row.last_time),
                    row.pos_x,
                    row.pos_y
                ])
        elif args == 'cesar_offline':
            query = CashCesar.query.filter(CashCesar.last_time < my_time.get_time_minus_three_days()).all()
            for row in query:
                ws.append([
                    row.unit_id,
                    row.object_name,
                    row.pin,
                    my_time.unix_to_moscow_time(row.created_at),
                    my_time.unix_to_moscow_time(row.last_time),
                    row.pos_x,
                    row.pos_y
                ])
        else:
            return None
    elif 'health' in args:
        if args == 'health_coordinates':
            ws.append(['Номер лота', 'Название в Wialon', 'Дистанция до объекта'])
            query = db.session.query(Transport, CashWialon).\
                join(CashWialon, CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))).\
                filter(Transport.x != 0).all()
            for transport, cash_wialon in query:
                wialon_pos = (cash_wialon.pos_y, cash_wialon.pos_x)
                if transport.x == 0:
                    continue
                work_pos = (transport.x, transport.y)
                delta = coord_math.calculate_distance(wialon_pos, work_pos) if cash_wialon.pos_y != 0 else None
                ws.append([transport.uNumber, cash_wialon.nm, delta])
        elif args == 'health_no_equip':
            ws.append(['uNumber', 'Кол-во wialon', 'Кол-во цезерей'])
            transports = Transport.query.all()
            for transport in transports:
                cesar_count = CashCesar.query.filter(
                    CashCesar.object_name.ilike(f'%{transport.uNumber}%')
                ).count()
                wialon_count = CashWialon.query.filter(
                    CashWialon.nm.ilike(f'%{transport.uNumber}%')
                ).count()
                ws.append([transport.uNumber, wialon_count, cesar_count])
        elif args == 'health_no_lot':
            ws.append(['Тип', 'Имя в системе'])
            transport_numbers = {t.uNumber for t in Transport.query.all()}
            for cesar in CashCesar.query.all():
                if not any(transport_number in cesar.object_name for transport_number in transport_numbers):
                    ws.append(['Cesar', cesar.object_name])
            for wialon in CashWialon.query.all():
                if not any(transport_number in wialon.nm for transport_number in transport_numbers):
                    ws.append(['Wialon', wialon.nm])
        else:
            return None
    elif "vopereator" in args:
        ws.append(['Date', 'uNumber', 'type', 'data', 'comment', 'comment_editor', 'region', 'storage', 'model', 'manager', 'customer'])
        alerts = Alert.query
        if args == "vopereator_theft_risk":
            alerts = alerts.filter(Alert.status == 0, Alert.type.in_(['distance', 'gps', 'no_docs_cords'])).all()
        elif args == "vopereator_nonworking_equipment":
            alerts = alerts.filter(Alert.status == 0, Alert.type == 'not_work').all()
        elif args == "vopereator_no_equipment":
            alerts = alerts.filter(Alert.status == 0, Alert.type == 'no_equipment').all()
        if alerts is None:
            return None
        for one_alerts in alerts:
            convert_date = my_time.unix_to_moscow_time(one_alerts.date)
            query = db.session.query(Transport, Storage, TransportModel).join(Storage,
                                                                             Transport.storage_id == Storage.ID).join(
                TransportModel, Transport.model_id == TransportModel.id)
            query = query.filter(Transport.uNumber == one_alerts.uNumber).first()
            ws.append([
                convert_date,
                one_alerts.uNumber,
                one_alerts.type,
                one_alerts.data,
                one_alerts.comment,
                one_alerts.comment_editor,
                query.Storage.region,
                query.Storage.name,
                query.TransportModel.name,
                query.Transport.manager,
                query.Transport.customer
            ])
    elif "main" in args:
        if args == "main_summary":
            ws.append(['Тип', 'Регион', 'Склад', '№ Лота', 'Модель', 'Тип подъемника', 'Тип двигателя', 'parser_1c', 'Cesar Position', 'Wialon'])
            query = (
                db.session.query(
                    TransportModel.type.label("transport_model_type"),
                    Storage.region.label("storage_region"),
                    Storage.name.label("storage_name"),
                    Transport.uNumber.label("transport_uNumber"),
                    TransportModel.name.label("transport_model_name"),
                    TransportModel.lift_type.label("transport_model_lift_type"),
                    TransportModel.engine.label("transport_model_engine"),
                    Transport.parser_1c.label('transport_parser_1c'),
                    db.session.query(func.count()).filter(
                        CashCesar.object_name.like(func.concat('%', Transport.uNumber, '%'))
                    ).label("cesar_count"),
                    db.session.query(func.count()).filter(
                        CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))
                    ).label("wialon_count"),
                )
                .join(TransportModel, Transport.model_id == TransportModel.id, isouter=True)
                .join(Storage, Transport.storage_id == Storage.ID, isouter=True)
            )
            results = query.all()
            for item in results:
                ws.append([
                    item.transport_model_type,
                    item.storage_region,
                    item.storage_name,
                    item.transport_uNumber,
                    item.transport_model_name,
                    item.transport_model_lift_type,
                    item.transport_model_engine,
                    item.transport_parser_1c,
                    item.cesar_count,
                    item.wialon_count
                ])
        elif args == "main_transport":
            ws.append(['ID', 'Storage ID', 'Model ID', '№ Лота', 'Год выпуска', 'VIN', 'X', 'Y', 'Клиент', 'Контакт клиента', 'Менеджер', 'Отключить виртуального оператора', 'parser_1c'])
            query = db.session.query(
                Transport.id,
                Transport.storage_id,
                Transport.model_id,
                Transport.uNumber,
                Transport.manufacture_year,
                Transport.vin,
                Transport.x,
                Transport.y,
                Transport.customer,
                Transport.customer_contact,
                Transport.manager,
                Transport.disable_virtual_operator,
                Transport.parser_1c
            )
            results = query.all()
            for item in results:
                ws.append([
                    item.id,
                    item.storage_id,
                    item.model_id,
                    item.uNumber or '',
                    item.manufacture_year or '',
                    item.vin or '',
                    item.x or '',
                    item.y or '',
                    item.customer or '',
                    item.customer_contact or '',
                    item.manager or '',
                    item.disable_virtual_operator,
                    item.parser_1c
                ])
        elif args == "main_transport_model":
            ws.append(['ID', 'Тип направления', 'Название', 'Тип подъемника', 'Двигатель', 'Страна', 'Тип техники', 'Бренд', 'Модель'])
            query = db.session.query(
                TransportModel.id,
                TransportModel.type,
                TransportModel.name,
                TransportModel.lift_type,
                TransportModel.engine,
                TransportModel.country,
                TransportModel.machine_type,
                TransportModel.brand,
                TransportModel.model
            )
            results = query.all()
            for item in results:
                ws.append([
                    item.id,
                    item.type or '',
                    item.name or '',
                    item.lift_type or '',
                    item.engine or '',
                    item.country or '',
                    item.machine_type or '',
                    item.brand or '',
                    item.model or ''
                ])
        elif args == "main_storage":
            ws.append(['ID', 'Название', 'Тип', 'Регион', 'Адрес', 'Организация'])
            query = db.session.query(
                Storage.ID,
                Storage.name,
                Storage.type,
                Storage.region,
                Storage.address,
                Storage.organization
            )
            results = query.all()
            for item in results:
                ws.append([
                    item.ID,
                    item.name or '',
                    item.type or '',
                    item.region or '',
                    item.address or '',
                    item.organization or ''
                ])
        else:
            return None
    else:
        return None

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def generate_and_send_report(args, user):
    report_entry = Reports(
        username=user.username,
        type=args,
        status='Генерация отчета'
    )
    db.session.add(report_entry)
    db.session.commit()

    try:
        report_content = filegen(args)

        if report_content is None:
            report_entry.status = 'Ошибка: Не удалось сгенерировать отчет'
            db.session.commit()
            return False

        subject = f'Отчет: {args}'
        body = f'Во вложении заказанный отчет {args}.'

        attachment_name = f'{args}.xlsx'

        success = mail_sender.send_email(
            user.email, subject, body, attachment_name, report_content
        )

        report_entry.status = 'Отчет отправлен' if success else 'Ошибка: Не удалось отправить отчет'
        db.session.commit()
        return success

    except Exception as e:
        db.session.rollback()
        report_entry.status = f'Ошибка: {str(e)}'
        db.session.add(report_entry)
        db.session.commit()
        return False