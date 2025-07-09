import jwt
from datetime import datetime, timedelta
from typing import Any
import os
import hashlib
from services.database import DatabaseService

SECRET_KEY = None
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480


def generate_and_store_secret_key():
    global SECRET_KEY
    # Generar una clave secreta aleatoria
    key = os.urandom(32)
    # Cifrar la clave (hash)
    hashed_key = hashlib.sha256(key).hexdigest()
    # Guardar en la base de datos (colección 'config')
    db = DatabaseService.get_db()
    db.config.update_one({"_id": "jwt_secret"}, {"$set": {"key": hashed_key}}, upsert=True)
    SECRET_KEY = hashed_key
    return hashed_key

def load_secret_key():
    global SECRET_KEY
    db = DatabaseService.get_db()
    config = db.config.find_one({"_id": "jwt_secret"})
    if config:
        SECRET_KEY = config["key"]
    return SECRET_KEY

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    if not SECRET_KEY:
        load_secret_key()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Any:
    if not SECRET_KEY:
        load_secret_key()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
