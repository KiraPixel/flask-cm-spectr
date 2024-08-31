import hashlib
import binascii
import os


def hash_password(password):
    SALT = os.getenv('SALT', b'r8\xcc\xf5\xf6\x8eq\xa3\xad\x0b8Y\xfc\x9f^\xaf')
    if not isinstance(SALT, bytes):
        SALT = SALT.encode('utf-8')
    hasher = hashlib.pbkdf2_hmac('sha256', password.encode(), SALT, 100000)
    return binascii.hexlify(hasher).decode()


def compare_passwords(stored_hashed_password, password):
    hashed_password = hash_password(password)
    return stored_hashed_password == hashed_password

