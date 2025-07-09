from fastapi import APIRouter, HTTPException, status, Depends, Form
from services.database import DatabaseService
from models.user_model import UserDB, CreateUser, UserResponse
from services.jwt_service import create_access_token, verify_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/users", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401, detail="Token inválido o expirado")
    return payload


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: CreateUser, current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    # Verificar si el usuario ya existe por email o nickname
    existing = await db.users.find_one({"$or": [{"email": user.email}, {"nickname": user.nickname}]})
    if existing:
        raise HTTPException(
            status_code=400, detail="El usuario ya existe con ese email o nickname.")
    # Guardar el usuario usando el método de la clase
    user_dict = await user.save_to_db()
    return user_dict


@router.post("/login")
async def login_user(nickname: str = Form(...), password: str = Form(...)):
    db = DatabaseService.get_db()
    user_data = await db.users.find_one({"nickname": nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = UserDB(**user_data)
    if not user.verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    # Generar JWT
    token_data = {"sub": user.nickname, "id": user.id, "rol": user.rol}
    access_token = create_access_token(token_data)
    user_dict = user.dict()
    user_dict.pop("password")
    user_response = UserResponse(**user_dict)
    return {"access_token": access_token, "token_type": "bearer", "user": user_response}


@router.post("/change-password")
async def change_password(nickname: str = Form(...), current_password: str = Form(...), new_password: str = Form(...), current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    user_data = await db.users.find_one({"nickname": nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = UserDB(**user_data)
    if not user.verify_password(current_password, user.password):
        raise HTTPException(
            status_code=401, detail="Contraseña actual incorrecta")
    # Hashear la nueva contraseña y actualizar
    from models.user_model import CreateUser
    hashed_new = CreateUser().hash_password(new_password)
    await db.users.update_one({"nickname": nickname}, {"$set": {"password": hashed_new}})
    return {"message": "Contraseña actualizada correctamente"}


@router.post("/update-contact")
async def update_contact(
    nickname: str = Form(...),
    email: str = Form(None),
    telefono: str = Form(None),
    current_password: str = Form(...),
    current_user=Depends(get_current_user)
):
    # Solo verificar que el JWT sea válido (no importa si el nickname coincide)
    db = DatabaseService.get_db()
    user_data = await db.users.find_one({"nickname": nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = UserDB(**user_data)
    if not user.verify_password(current_password, user.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    update_fields = {}
    if email:
        update_fields["email"] = email
    if telefono:
        update_fields["telefono"] = telefono
    if not update_fields:
        raise HTTPException(
            status_code=400, detail="Debes proporcionar al menos un campo a actualizar")
    await db.users.update_one({"nickname": nickname}, {"$set": update_fields})
    return {"message": "Datos de contacto actualizados correctamente"}
