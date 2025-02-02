from flask import Blueprint, request, render_template, jsonify
from .models import db, Transport, Storage, TransportModel
import json
from sqlalchemy import func


sbi = Blueprint('sbi', __name__)

@sbi.route('/')
def index():
    # Данные для круговой диаграммы (общий подсчет техники по регионам)
    region_query = db.session.query(
        Storage.region,
        func.count(Transport.id).label('car_count')
    ).join(Transport, Transport.storage_id == Storage.ID) \
        .group_by(Storage.region) \
        .all()

    region_data = [{'region': region, 'car_count': car_count} for region, car_count in region_query]
    print("Region Data:", region_query)  # Вывод данных в терминал для проверки
    print("region_data перед отправкой в шаблон:", region_data)

    # Данные для столбчатой диаграммы (разделение по типам техники)
    query = db.session.query(
        Storage.region,
        TransportModel.type,
        func.count(Transport.id).label('car_count')
    ).join(Transport, Transport.storage_id == Storage.ID) \
        .join(TransportModel, Transport.model_id == TransportModel.id) \
        .group_by(Storage.region, TransportModel.type) \
        .all()

    # Преобразуем данные в удобный формат для диаграммы
    chart_data = {}
    for region, type_, count in query:
        if region not in chart_data:
            chart_data[region] = {}
        chart_data[region][type_] = count

    # Возвращаем данные в шаблон
    return render_template('sbi/main.html', region_data=region_data, chart_data=chart_data)
