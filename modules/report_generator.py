import io
import tempfile

from sqlalchemy import func

from app.models import Transport, CashCesar, CashWialon, Reports, Alert, TransportModel, Storage
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
            output.write('Номер лота,Название в Wialon,Дистанция до объекта' + '\n')
            query = db.session.query(Transport, CashWialon). \
                join(CashWialon, CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))). \
                filter(Transport.x != 0). \
                all()
            for transport, cash_wialon in query:
                wialon_pos = (cash_wialon.pos_y, cash_wialon.pos_x)
                if transport.x == 0:
                    continue
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
    elif "vopereator" in args:
        output.write('Date,uNumber,type,data' + '\n')
        alerts = Alert.query
        if args == "vopereator_theft_risk":
            alerts = alerts.filter(Alert.status == 0, Alert.type == 'distance').all()
        elif args == "vopereator_nonworking_equipment":
            alerts = alerts.filter(Alert.status == 0, Alert.type == 'not_work').all()
        elif args == "vopereator_no_equipment":
            alerts = alerts.filter(Alert.status == 0, Alert.type == 'no_equipment').all()
        if alerts is None:
            return None
        for one_alerts in alerts:
            convert_date = my_time.unix_to_moscow_time(one_alerts.date)
            final_str = f'{convert_date},{one_alerts.uNumber},{one_alerts.type},{one_alerts.data}'
            output.write(final_str + '\n')
    elif "main" in args:
        if args == "main_summary":
            output.write('Тип;Регион;Склад;№ Лота;Модель;Тип подъемника;Тип двигателя;Cesar Position;Wialon' + '\n')
            query = (
                db.session.query(
                    TransportModel.type.label("transport_model_type"),
                    Storage.region.label("storage_region"),
                    Storage.name.label("storage_name"),
                    Transport.uNumber.label("transport_uNumber"),
                    TransportModel.name.label("transport_model_name"),
                    TransportModel.lift_type.label("transport_model_lift_type"),
                    TransportModel.engine.label("transport_model_engine"),
                    # Подзапрос для подсчета количества записей в CashCesar
                    db.session.query(func.count()).filter(
                        CashCesar.object_name.like(func.concat('%', Transport.uNumber, '%'))
                    ).label("cesar_count"),
                    # Подзапрос для подсчета количества записей в CashWialon
                    db.session.query(func.count()).filter(
                        CashWialon.nm.like(func.concat('%', Transport.uNumber, '%'))
                    ).label("wialon_count"),
                )
                # LEFT JOIN с транспортной моделью
                .join(TransportModel, Transport.model_id == TransportModel.id, isouter=True)
                # LEFT JOIN со складом
                .join(Storage, Transport.storage_id == Storage.ID, isouter=True)
            )
            results = query.all()
            for item in results:
                final_str = f"{item.transport_model_type};{item.storage_region};{item.storage_name};" \
                            f"{item.transport_uNumber};{item.transport_model_name};" \
                            f"{item.transport_model_lift_type};{item.transport_model_engine};" \
                            f"{item.cesar_count};{item.wialon_count}"
                output.write(final_str + '\n')
        elif args == "main_transport":
                output.write(
                    'ID;Storage ID;Model ID;№ Лота;Год выпуска;VIN;X;Y;Клиент;Контакт клиента;Менеджер;Отключить виртуального оператора\n')

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
                    Transport.disable_virtual_operator
                )

                results = query.all()
                for item in results:
                    final_str = f"{item.id};{item.storage_id};{item.model_id};{item.uNumber or ''};" \
                                f"{item.manufacture_year or ''};{item.vin or ''};" \
                                f"{item.x or ''};{item.y or ''};" \
                                f"{item.customer or ''};{item.customer_contact or ''};" \
                                f"{item.manager or ''};{item.disable_virtual_operator or ''}"
                    output.write(final_str + '\n')
        elif args == "main_transport_model":
            output.write('ID;Тип;Название;Тип подъемника;Двигатель;Страна\n')

            query = db.session.query(
                TransportModel.id,
                TransportModel.type,
                TransportModel.name,
                TransportModel.lift_type,
                TransportModel.engine,
                TransportModel.country
            )

            results = query.all()
            for item in results:
                final_str = f"{item.id};{item.type or ''};{item.name or ''};" \
                            f"{item.lift_type or ''};{item.engine or ''};{item.country or ''}"
                output.write(final_str + '\n')
        elif args == "main_storage":
            output.write('ID;Название;Тип;Регион;Адрес;Организация\n')

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
                final_str = f"{item.ID};{item.name or ''};{item.type or ''};" \
                            f"{item.region or ''};{item.address or ''};{item.organization or ''}"
                output.write(final_str + '\n')
    else:
        return None

    output.seek(0)
    return output.getvalue()


def generate_and_send_report(args, user):
    # Создание записи в БД о начале генерации отчета
    report_entry = Reports(
        username=user.username,
        type=args,
        status='Генерация отчета'
    )
    db.session.add(report_entry)
    db.session.commit()  # Коммитим, чтобы получить id записи

    try:
        # Генерация отчета
        report_content = filegen(args)

        if report_content is None:
            report_entry.status = 'Ошибка: Не удалось сгенерировать отчет'
            db.session.commit()
            return False

        # Генерация письма
        subject = f'Отчет: {args}'
        body = f'Во вложении заказанный отчет {args}.'

        # Создание CSV с BOM
        attachment_name = f'{args}.csv'
        bom = '\ufeff'
        report_content_with_bom = bom + report_content

        # Отправка письма
        success = mail_sender.send_email(
            user.email, subject, body, attachment_name, report_content_with_bom.encode('utf-8')
        )

        # Обновление статуса в зависимости от успеха
        report_entry.status = 'Отчет отправлен' if success else 'Ошибка: Не удалось отправить отчет'
        db.session.commit()
        return success

    except Exception as e:
        # Откат транзакции при возникновении ошибки
        db.session.rollback()
        report_entry.status = f'Ошибка: {str(e)}'
        db.session.add(report_entry)
        db.session.commit()  # Сохраняем новый статус с сообщением об ошибке
        return False

