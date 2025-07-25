from fastapi import APIRouter, HTTPException, status, Form
from services.database import DatabaseService
from models.user_model import UserDB, UserResponse
from models.admin_model import Admin
from services.jwt_service import create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login")
async def login_user(nickname: str = Form(...), password: str = Form(...)):
    """
    Endpoint de autenticación para usuarios regulares
    """
    db = DatabaseService.get_db()
    user_data = await db.users.find_one({"nickname": nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Convertir ObjectId a string si existe
    if "_id" in user_data:
        user_data["id"] = str(user_data.pop("_id"))
    
    user = UserDB(**user_data)
    if not user.verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    # Generar JWT
    token_data = {"sub": user.nickname, "id": user.id, "rol": user.rol, "tipo": "user"}
    access_token = create_access_token(token_data)
    
    user_dict = user.dict()
    user_dict.pop("password")
    user_response = UserResponse(**user_dict)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user": user_response,
        "user_type": "user"
    }

@router.post("/admin-login")
async def login_admin(nickname: str = Form(...), password: str = Form(...)):
    """
    Endpoint de autenticación para administradores
    """
    db = DatabaseService.get_db()
    admin_data = await db.admins.find_one({"nickname": nickname})
    if not admin_data:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")
    
    admin = Admin(admin_data["password"])
    if not admin.verify_password(password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    # Generar JWT para admin
    token_data = {
        "sub": admin_data["nickname"], 
        "id": str(admin_data["_id"]),
        "rol": "Administrador",
        "tipo": "admin"
    }
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "admin": {
            "nickname": admin_data["nickname"],
            "nombre": admin_data.get("nombre", ""),
            "apellido_paterno": admin_data.get("apellido_paterno", ""),
            "apellido_materno": admin_data.get("apellido_materno", "")
        },
        "user_type": "admin"
    }