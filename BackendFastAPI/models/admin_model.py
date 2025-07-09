import hashlib

class Admin:
    def __init__(self, nickname: str, password_hashed: str):
        self.nickname = nickname
        self.password_hashed = password_hashed

    def verify(self, nickname: str, password: str) -> bool:
        if self.nickname != nickname:
            return False
        try:
            salt, stored_hash = self.password_hashed.split(":")
            salt = bytes.fromhex(salt)
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return new_hash.hex() == stored_hash
        except Exception:
            return False
