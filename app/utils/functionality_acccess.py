import json

from sqlalchemy.exc import SQLAlchemyError

from app.models import FunctionalityAccess, User


def validate_functionality_roles(roles):
    if roles is None:
        return True, [], None

    errors = []
    validated_roles = []

    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
            if not isinstance(roles, list):
                return False, ['functionality_roles должен быть списком или null'], None
        except json.JSONDecodeError:
            return False, ['Неверный формат строки functionality_roles, ожидается JSON-массив'], None
    elif not isinstance(roles, list):
        return False, ['functionality_roles должен быть списком или null'], None

    valid_role_ids = {role.id for role in FunctionalityAccess.query.all()}
    for role_id in roles:
        if not isinstance(role_id, int):
            errors.append(f'Идентификатор роли {role_id} должен быть целым числом')
        elif role_id not in valid_role_ids:
            errors.append(f'Роль с идентификатором {role_id} не существует')
        else:
            validated_roles.append(role_id)

    return len(errors) == 0, errors, validated_roles


def get_user_roles(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return []

        functionality_roles = user.functionality_roles
        if not functionality_roles:
            return []

        try:
            role_ids = json.loads(functionality_roles)
            if not isinstance(role_ids, list):
                return []
        except json.JSONDecodeError:
            return []

        roles = FunctionalityAccess.query.filter(FunctionalityAccess.id.in_(role_ids)).all()
        role_names = [role.name for role in roles if role.name]
        return role_names

    except SQLAlchemyError:
        return []


def has_role_access(username, rolename):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return False

        functionality_roles = user.functionality_roles
        if not functionality_roles:
            return False

        try:
            role_ids = json.loads(functionality_roles)
            if not isinstance(role_ids, list):
                return False
        except json.JSONDecodeError:
            return False

        role = FunctionalityAccess.query.filter_by(name=rolename).first()
        if not role:
            return False

        return role.id in role_ids

    except SQLAlchemyError:
        return False