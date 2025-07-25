import hashlib
import os

class Admin:
    def __init__(self, password_hashed: str):
        self.password_hashed = password_hashed

    def verify_password(self, password: str) -> bool:
        try:
            salt, stored_hash = self.password_hashed.split(":")
            salt = bytes.fromhex(salt)
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return new_hash.hex() == stored_hash
        except Exception:
            return False

    @staticmethod
    def hash_password(password: str) -> str:
        salt = os.urandom(16)
        hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ':' + hashed_password.hex()
