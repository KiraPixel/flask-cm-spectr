import io
import logging
import time
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from openpyxl import Workbook
from sqlalchemy import func, text
from app.models import Transport, CashCesar, CashWialon, Reports, Alert, TransportModel, Storage, custom_transport_transfer
from app.utils import get_address_from_coords
from . import my_time, coord_math
from app import db
from modules import mail_sender

logger = logging.getLogger('flask_cm_spectr')

# Константы
MAX_ATTEMPTS = 50  # Максимальное количество попыток получения адреса
SLEEP_INTERVAL = 5  # Интервал ожидания между попытками (в секундах)
ADDRESS_TIMEOUT = "Time out to convert"  # Сообщение при таймауте конвертации адреса
DEFAULT_ADDRESS = "Error convert"  # Адрес по умолчанию при неудаче
THREE_DAYS_AGO = my_time.get_time_minus_three_days()

# Конфигурация отчетов
REPORT_CONFIGS = {
    'wialon': {
        'headers': ['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'x', 'y'],
        'query': lambda: CashWialon.query.all(),
        'row_builder': lambda row: [
            row.id,
            row.nm,
            row.uid,
            my_time.unix_to_moscow_time(row.last_time),
            my_time.unix_to_moscow_time(row.last_pos_time),
            row.pos_x,
            row.pos_y
        ]
    },
    'wialon_with_address': {
        'headers': ['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'address'],
        'query': lambda: CashWialon.query.all(),
        'row_builder': lambda row: [
            row.id,
            row.nm,
            row.uid,
            my_time.unix_to_moscow_time(row.last_time),
            my_time.unix_to_moscow_time(row.last_pos_time),
            get_location(row.pos_y, row.pos_x)
        ]
    },
    'wialon_offline': {
        'headers': ['wialon_id', 'uNumber', 'uid', 'last_time', 'last_pos_time', 'x', 'y'],
        'query': lambda: CashWialon.query.filter(CashWialon.last_time < THREE_DAYS_AGO).all(),
        'row_builder': lambda row: [
            row.id,
            row.nm,
            row.uid,
            my_time.unix_to_moscow_time(row.last_time),
            my_time.unix_to_moscow_time(row.last_pos_time),
            row.pos_x,
            row.pos_y
        ]
    },
    'cesar': {
        'headers': ['cesar_id', 'uNumber', 'PIN', 'created', 'last_online', 'x', 'y'],
        'query': lambda: CashCesar.query.all(),
        'row_builder': lambda row: [
            row.unit_id,
            row.object_name,
            row.pin,
            my_time.unix_to_moscow_time(row.created_at),
            my_time.unix_to_moscow_time(row.last_time),
            row.pos_x,
            row.pos_y
        ]
    },
    'cesar_with_address': {
        'headers': ['cesar_id', 'uNumber', 'PIN', 'last_online', 'address', 'x', 'y'],
        'query': lambda: CashCesar.query.all(),
        'row_builder': lambda row: [
            row.unit_id,
            row.object_name,
            row.pin,
            my_time.unix_to_moscow_time(row.last_time),
            get_location(row.pos_x, row.pos_y),
            row.pos_x,
            row.pos_y
        ]
    },
    'cesar_offline': {
        'headers': ['cesar_id', 'uNumber', 'PIN', 'last_time'],
        'query': lambda: CashCesar.query.filter(CashCesar.last_time < THREE_DAYS_AGO).all(),
        'row_builder': lambda row: [
            row.unit_id,
            row.object_name,
            row.pin,
            my_time.unix_to_moscow_time(row.last_time)
        ]
    },
    'health_coordinates': {
        'headers': ['Номер лота', 'Название в Wialon', 'Дистанция до объекта'],
        'query': lambda: db.session.query(Transport, CashWialon)
        .join(CashWialon, CashWialon.nm.like(func.concat('%', Transport.uNumber, '%')))
        .filter(Transport.x != 0).all(),
        'row_builder': lambda row: build_health_coordinates_row(row)
    },
    'health_no_equip': {
        'headers': ['uNumber', 'Кол-во wialon', 'Кол-во цезерей'],
        'query': lambda: Transport.query.all(),
        'row_builder': lambda row: [
            row.uNumber,
            CashWialon.query.filter(CashWialon.nm.ilike(f'%{row.uNumber}%')).count(),
            CashCesar.query.filter(CashCesar.object_name.ilike(f'%{row.uNumber}%')).count()
        ]
    },
    'health_no_lot': {
        'headers': ['Тип', 'Имя в системе', 'WialonID/PIN'],
        'query': lambda: get_health_no_lot_data(),
        'row_builder': lambda row: row
    },
    'vopereator_theft_risk': {
        'headers': ['Date', 'uNumber', 'type', 'data', 'comment', 'comment_editor', 'region', 'storage', 'model',
                    'manager', 'customer'],
        'query': lambda: Alert.query.filter(Alert.status == 0,
                                            Alert.type.in_(['distance', 'gps', 'no_docs_cords'])).all(),
        'row_builder': lambda row: build_voperator_row(row)
    },
    'vopereator_nonworking_equipment': {
        'headers': ['Date', 'uNumber', 'type', 'data', 'comment', 'comment_editor', 'region', 'storage', 'model',
                    'manager', 'customer'],
        'query': lambda: Alert.query.filter(Alert.status == 0, Alert.type == 'not_work').all(),
        'row_builder': lambda row: build_voperator_row(row)
    },
    'vopereator_no_equipment': {
        'headers': ['Date', 'uNumber', 'type', 'data', 'comment', 'comment_editor', 'region', 'storage', 'model',
                    'manager', 'customer'],
        'query': lambda: Alert.query.filter(Alert.status == 0, Alert.type == 'no_equipment').all(),
        'row_builder': lambda row: build_voperator_row(row)
    },
    'main_summary': {
        'headers': ['Тип', 'Регион', 'Склад', '№ Лота', 'Модель', 'Тип подъемника', 'Тип двигателя', 'parser_1c',
                    'Cesar Position', 'Wialon'],
        'query': lambda: db.session.query(
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
        .join(Storage, Transport.storage_id == Storage.ID, isouter=True).all(),
        'row_builder': lambda row: [
            row.transport_model_type,
            row.storage_region,
            row.storage_name,
            row.transport_uNumber,
            row.transport_model_name,
            row.transport_model_lift_type,
            row.transport_model_engine,
            row.transport_parser_1c,
            row.cesar_count,
            row.wialon_count
        ]
    },
    'main_transport': {
        'headers': ['ID', 'Storage ID', 'Model ID', '№ Лота', 'Год выпуска', 'VIN', 'X', 'Y', 'Клиент',
                    'Контакт клиента', 'Менеджер', 'parser_1c'],
        'query': lambda: db.session.query(
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
            Transport.parser_1c
        ).all(),
        'row_builder': lambda row: [
            row.id,
            row.storage_id,
            row.model_id,
            row.uNumber or '',
            row.manufacture_year or '',
            row.vin or '',
            row.x or '',
            row.y or '',
            row.customer or '',
            row.customer_contact or '',
            row.manager or '',
            row.parser_1c
        ]
    },
    'main_transport_model': {
        'headers': ['ID', 'Тип направления', 'Название', 'Тип подъемника', 'Двигатель', 'Страна', 'Тип техники',
                    'Бренд', 'Модель'],
        'query': lambda: db.session.query(
            TransportModel.id,
            TransportModel.type,
            TransportModel.name,
            TransportModel.lift_type,
            TransportModel.engine,
            TransportModel.country,
            TransportModel.machine_type,
            TransportModel.brand,
            TransportModel.model
        ).all(),
        'row_builder': lambda row: [
            row.id,
            row.type or '',
            row.name or '',
            row.lift_type or '',
            row.engine or '',
            row.country or '',
            row.machine_type or '',
            row.brand or '',
            row.model or ''
        ]
    },
    'main_storage': {
        'headers': ['ID', 'Название', 'Тип', 'Регион', 'Адрес', 'Организация'],
        'query': lambda: db.session.query(
            Storage.ID,
            Storage.name,
            Storage.type,
            Storage.region,
            Storage.address,
            Storage.organization
        ).all(),
        'row_builder': lambda row: [
            row.ID,
            row.name or '',
            row.type or '',
            row.region or '',
            row.address or '',
            row.organization or ''
        ]
    },
    'custom_transport_transfer': {
        'headers': ['uNumber', 'name', 'region', 'type', 'model_name', 'formatted_date',
                   'wialon_uid_count', 'wialon_last_time', 'cesar_pin_count'],
        'query': lambda **params: custom_transport_transfer(
            start_date=params.get('date_from'),
            end_date=params.get('date_to'),
            regions=[r.strip() for r in params.get('region', '').replace('\n', ',').split(',') if r.strip()] if params.get('region') else [],
            home_storage=params.get('only_home_storages') == 'on'
        ),
        'row_builder': lambda row: [row.get(col, '') for col in ['uNumber', 'name', 'region', 'type', 'model_name',
                                                                 'formatted_date', 'wialon_uid_count', 'wialon_last_time', 'cesar_pin_count']]
    }
}

def get_location(x: float, y: float) -> str:
    """Получение адреса по координатам с механизмом повторных попыток."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            location = str(get_address_from_coords(x, y))
            if location != ADDRESS_TIMEOUT:
                return location
        except Exception as e:
            logger.debug(f"Попытка {attempt + 1} из {MAX_ATTEMPTS} получения адреса не удалась: {e}")
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(SLEEP_INTERVAL)
    return DEFAULT_ADDRESS


def build_health_coordinates_row(row: Tuple[Transport, CashWialon]) -> List:
    """Формирование строки для отчета health_coordinates."""
    transport, cash_wialon = row
    if transport.x == 0:
        return None
    wialon_pos = (cash_wialon.pos_y, cash_wialon.pos_x)
    work_pos = (transport.x, transport.y)
    delta = coord_math.calculate_distance(wialon_pos, work_pos) if cash_wialon.pos_y != 0 else None
    return [transport.uNumber, cash_wialon.nm, delta]


def get_health_no_lot_data() -> List[List[str]]:
    """Генерация данных для отчета health_no_lot."""
    transport_numbers = {t.uNumber for t in Transport.query.all()}
    result = []
    for cesar in CashCesar.query.all():
        if not any(transport_number in cesar.object_name for transport_number in transport_numbers):
            result.append(['Cesar', cesar.object_name, cesar.pin])
    for wialon in CashWialon.query.all():
        if not any(transport_number in wialon.nm for transport_number in transport_numbers):
            result.append(['Wialon', wialon.nm, wialon.uid])
    return result


def build_voperator_row(alert: Alert) -> List:
    """Формирование строки для отчетов vopereator."""
    query = db.session.query(Transport, Storage, TransportModel) \
        .join(Storage, Transport.storage_id == Storage.ID) \
        .join(TransportModel, Transport.model_id == TransportModel.id) \
        .filter(Transport.uNumber == alert.uNumber).first()

    return [
        my_time.unix_to_moscow_time(alert.date),
        alert.uNumber,
        alert.type,
        alert.data,
        alert.comment,
        alert.comment_editor,
        query.Storage.region if query else '',
        query.Storage.name if query else '',
        query.TransportModel.name if query else '',
        query.Transport.manager if query else '',
        query.Transport.customer if query else ''
    ]


def generate_excel_report(report_type: str, **params) -> Optional[bytes]:
    """Генерация Excel-отчета на основе типа отчета и параметров."""
    if report_type not in REPORT_CONFIGS:
        return None

    config = REPORT_CONFIGS[report_type]
    wb = Workbook()
    ws = wb.active
    ws.append(config['headers'])

    # Вызов query с параметрами
    query_result = config['query'](**params) if params else config['query']()
    if not query_result:  # Проверка на False или пустой результат
        return None

    for row in query_result:
        row_data = config['row_builder'](row)
        if row_data:  # Пропуск строк None (например, отфильтрованных в health_coordinates)
            ws.append(row_data)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_and_send_report(report_id: str, user, **params) -> bool:
    """Генерация и отправка отчета пользователю."""
    report_entry = Reports(
        username=user.username,
        type=report_id,
        status='Генерация отчета'
    )
    db.session.add(report_entry)
    db.session.commit()

    try:
        # Генерация отчета с учетом параметров
        report_content = generate_excel_report(report_id, **params)
        if report_content is None:
            report_entry.status = 'Ошибка: Не удалось сгенерировать отчет'
            db.session.commit()
            return False

        # Формирование темы и тела письма
        subject = f'Отчет: {report_id}'
        if params:
            params_str = ', '.join(f"{key}: {value}" for key, value in params.items())
            body = f'Во вложении заказанный отчет "{report_id}" с параметрами: {params_str}.'
        else:
            body = f'Во вложении заказанный отчет "{report_id}".'

        attachment_name = f'{report_id}.xlsx'

        # Отправка письма
        success = mail_sender.send_email(
            user.email,
            subject,
            body,
            attachment_name=attachment_name,
            attachment_content=report_content
        )

        report_entry.status = 'Отчет отправлен' if success else 'Ошибка: Не удалось отправить отчет'
        db.session.commit()
        return success

    except Exception as e:
        db.session.rollback()
        report_entry.status = f'Ошибка: {str(e)}'
        db.session.commit()
        return False