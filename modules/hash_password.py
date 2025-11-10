import base64
import hashlib
import binascii
import os
import secrets
import string


def generator_password():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))


def hash_password(password):
    SALT = os.getenv('SALT', b'r8\xcc\xf5\xf6\x8eq\xa3\xad\x0b8Y\xfc\x9f^\xaf')
    if SALT is None:
        SALT = b'r8\xcc\xf5\xf6\x8eq\xa3\xad\x0b8Y\xfc\x9f^\xaf'  # дефолт
    else:
        SALT = base64.b64decode(SALT)
    hasher = hashlib.pbkdf2_hmac('sha256', password.encode(), SALT, 100000)
    return binascii.hexlify(hasher).decode()


def compare_passwords(stored_hashed_password, password):
    hashed_password = hash_password(password)
    return stored_hashed_password == hashed_password

