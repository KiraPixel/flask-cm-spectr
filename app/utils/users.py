from app.models import User, db


def create_new_user(email, username, h_password):
    try:
        new_user = User(
            username=username,
            email=email,
            password=h_password,
            role=-1,
            last_activity="1999-12-02 00:00:00",
            transport_access='"[]"',
            functionality_roles='"[]"'
        )
        db.session.add(new_user)
        db.session.commit()

        user = User.query.filter_by(username=username, email=email).first()
        if user:
            return True
        else:
            return False
    except Exception as e:
        print(f'При создании нового пользователя произошла ошибка {e}')
        db.session.rollback()
        return False