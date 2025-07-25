from typing import Literal, Optional
from pydantic import BaseModel, Field, validator
import hashlib
import os
import re

class UserBase(BaseModel):
    nombre: str = Field(..., description="Nombre del usuario")
    apellido_paterno: str = Field(..., description="Apellido paterno del usuario")
    apellido_materno: str = Field(..., description="Apellido materno del usuario")
    nickname: Optional[str] = Field(None, description="Nombre de usuario")
    email: Optional[str] = Field(None, description="Correo electrónico del usuario")
    telefono: Optional[str] = Field(None, description="Teléfono del usuario")
    rol: Literal['Administrador','Inspector','Supervisor','Operador','Empleado','Dev'] = Field(..., description="Rol del usuario")

class UserDB(UserBase):
    id: Optional[str] = Field(..., description="ID del usuario (ObjectId de MongoDB)")
    password: str = Field(..., description="Contraseña del usuario")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        salt, stored_hash = hashed_password.split(':')
        salt = bytes.fromhex(salt)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_hash.hex() == stored_hash

    @validator('id')
    def validate_objectid(cls, v):
        if v is not None and not re.fullmatch(r"^[a-fA-F0-9]{24}$", v):
            raise ValueError("El id debe ser un ObjectId válido de MongoDB (24 caracteres hexadecimales)")
        return v

class CreateUser(UserBase):
    password: Optional[str] = Field(None, description="Contraseña del usuario")

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        hashed_password = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ':' + hashed_password.hex()

    async def save_to_db(self):
        from services.database import DatabaseService
        db = DatabaseService.get_db()
        user_dict = self.dict()
        user_dict["password"] = self.hash_password(self.password)
        result = await db.users.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
        user_dict.pop("password")  # Eliminar password del resultado
        user_dict.pop("_id", None)  # Eliminar _id de MongoDB si existe
        return user_dict
 
class UserResponse(UserBase):
    nickname: str = Field(..., description="Nombre de usuario")