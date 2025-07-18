import json
from sqlalchemy import or_, and_
from app.models import User, Transport, db, Storage



def normalize_transport_access(transport_access):
    """Нормализует правила доступа к транспорту из JSON или списка в список словарей."""
    if not transport_access:
        return []
    if isinstance(transport_access, str):
        try:
            transport_access = json.loads(transport_access)
        except json.JSONDecodeError:
            return []
    return (
        transport_access
        if isinstance(transport_access, list) and all(isinstance(rule, dict) for rule in transport_access)
        else []
    )


def validate_transport_access_rules(rules):
    errors = []
    rules = normalize_transport_access(rules)
    if not rules:
        return True, []  # Пустой список валиден

    valid_types = {"OR", "AND", "AND NOT", "ALL"}
    valid_params = {"uNumber", "manager", "region"}

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"Правило {i + 1}: должно быть словарем")
            continue
        if not all(key in rule for key in ("type", "param", "value")):
            errors.append(f"Правило {i + 1}: отсутствуют ключи type, param или value")
            continue
        rule_type, param, value = rule["type"], rule["param"], rule["value"]
        if rule_type not in valid_types:
            errors.append(f"Правило {i + 1}: неверный тип '{rule_type}', ожидается {valid_types}")
        if rule_type == "ALL":
            if param != "" or value != "":
                errors.append(f"Правило {i + 1}: для типа ALL param и value должны быть пустыми")
        else:
            if param not in valid_params:
                errors.append(f"Правило {i + 1}: неверный параметр '{param}', ожидается {valid_params}")
            if not value:
                errors.append(f"Правило {i + 1}: value не должно быть пустым для типа {rule_type}")

    return not errors, errors


def _get_current_value(transport, storage, param, u_number):
    return (
        u_number if param == "uNumber"
        else transport.manager if param == "manager"
        else storage.region if param == "region" and storage
        else None
    )


def check_access_to_transport(username, u_number):
    """Проверяет, есть ли у пользователя доступ к транспорту."""
    user = User.query.filter_by(username=username).first_or_404()
    if user.role == 1:
        return True
    transport = db.session.query(Transport).filter(Transport.uNumber == u_number).first()
    if not transport:
        return False
    storage = (
            db.session.query(Storage)
            .filter_by(ID=transport.storage_id)
            .first() or
            db.session.query(Storage).filter_by(ID=0).first()
    )
    if not storage:
        return False
    rules = normalize_transport_access(user.transport_access)
    if not rules:
        return False
    has_all_rule = any(rule["type"] == "ALL" for rule in rules)
    or_met, and_met = False, True
    or_exist, and_exist = False, False
    for rule in rules:
        if rule["type"] == "ALL":
            continue
        param, value, rule_type = rule["param"], rule["value"], rule["type"]
        current_value = _get_current_value(transport, storage, param, u_number)
        if rule_type == "OR":
            or_exist = True
            or_met |= current_value == value
        elif rule_type == "AND":
            and_exist = True
            and_met &= current_value == value
        elif rule_type == "AND NOT" and current_value == value:
            return False
    return has_all_rule or (not or_exist or or_met) and (not and_exist or and_met)


def _build_rule_conditions(rules):
    """Группирует правила по типу и параметру для построения SQL-запроса."""
    conditions = {
        "OR": {"uNumber": [], "manager": [], "region": []},
        "AND": {"uNumber": [], "manager": [], "region": []},
        "AND NOT": {"uNumber": [], "manager": [], "region": []}
    }
    has_all_rule = False
    for rule in rules:
        if rule["type"] == "ALL":
            has_all_rule = True
            continue
        param, value, rule_type = rule["param"], rule["value"], rule["type"]
        conditions[rule_type][param].append(value)
    return conditions, has_all_rule


def _build_sql_filters(conditions, has_all_rule):
    """Строит SQL-фильтры для условий OR, AND и AND NOT."""
    filters = []

    # AND NOT фильтры
    not_filters = []
    if conditions["AND NOT"]["uNumber"]:
        not_filters.append(~Transport.uNumber.in_(conditions["AND NOT"]["uNumber"]))
    if conditions["AND NOT"]["manager"]:
        not_filters.append(~Transport.manager.in_(conditions["AND NOT"]["manager"]))
    if conditions["AND NOT"]["region"]:
        not_filters.append(or_(~Storage.region.in_(conditions["AND NOT"]["region"]), Storage.ID == 0))
    if not_filters:
        filters.append(and_(*not_filters))

    if has_all_rule:
        return filters if filters else [True]  # Разрешить все, если нет AND NOT

    # OR фильтры
    or_filters = []
    if conditions["OR"]["uNumber"]:
        or_filters.append(Transport.uNumber.in_(conditions["OR"]["uNumber"]))
    if conditions["OR"]["manager"]:
        or_filters.append(Transport.manager.in_(conditions["OR"]["manager"]))
    if conditions["OR"]["region"]:
        or_filters.append(or_(Storage.region.in_(conditions["OR"]["region"]), Storage.ID == 0))
    if or_filters:
        filters.append(or_(*or_filters))

    # AND фильтры
    and_filters = []
    if conditions["AND"]["uNumber"]:
        and_filters.append(Transport.uNumber.in_(conditions["AND"]["uNumber"]))
    if conditions["AND"]["manager"]:
        and_filters.append(Transport.manager.in_(conditions["AND"]["manager"]))
    if conditions["AND"]["region"]:
        and_filters.append(or_(Storage.region.in_(conditions["AND"]["region"]), Storage.ID == 0))
    if and_filters:
        filters.append(and_(*and_filters))

    return filters if filters else [False]  # Запретить все, если нет условий


def get_all_access_transport(username):
    """Получает все uNumber транспорта, доступные пользователю."""
    user = User.query.filter_by(username=username).first_or_404()
    if user.role == 1:
        return [t.uNumber for t in Transport.query.all()]

    rules = normalize_transport_access(user.transport_access)
    if not rules:
        return []

    conditions, has_all_rule = _build_rule_conditions(rules)
    query = Transport.query.outerjoin(Storage, Transport.storage_id == Storage.ID)
    filters = _build_sql_filters(conditions, has_all_rule)

    return list(set(t.uNumber for t in query.filter(and_(*filters)).all()))

