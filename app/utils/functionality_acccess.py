import json

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError

from app.models import FunctionalityAccess, User, db


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


def get_user_roles(user: User):
    try:
        functionality_roles = user.functionality_roles
        if not functionality_roles:
            return []
        roles = FunctionalityAccess.query.filter(FunctionalityAccess.id.in_(functionality_roles)).all()
        role_names = [role.name for role in roles if role.name]
        return role_names

    except Exception as e:
        print(f"Error: {e}")
        return []


def has_role_access(username, rolename):
    try:
        if not isinstance(username, str) or not isinstance(rolename,str) or not username.strip() or not rolename.strip():
            return False

        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        elif user.role == 1:
            return True
        elif user.functionality_roles is None:
            return False

        user_roles = get_user_roles(user)
        if rolename in user_roles:
            return True

        return False

    except Exception as e:
        print(f"Error: {e}")
        return False