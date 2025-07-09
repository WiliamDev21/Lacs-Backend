from fastapi import APIRouter, HTTPException, status, Depends, Form
from services.database import DatabaseService
from models.user_model import CreateUser
from models.admin_model import Admin
from services.jwt_service import verify_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/admin", tags=["admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return payload

@router.post("/create-user", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    admin_nickname: str = Form(...),
    admin_password: str = Form(...),
    nombre: str = Form(...),
    apellido_paterno: str = Form(...),
    apellido_materno: str = Form(...),
    nickname: str = Form(...),
    empresa: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
    rol: str = Form(...)
):
    db = DatabaseService.get_db()
    # Validar admin como entidad separada
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    # Validar que el usuario no exista
    existing = await db.users.find_one({"$or": [{"email": email}, {"nickname": nickname}]})
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe con ese email o nickname.")
    # Crear usuario
    user = CreateUser(
        nombre=nombre,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
        nickname=nickname,
        empresa=empresa,
        password=password,
        email=email,
        telefono=telefono,
        rol=rol
    )
    user_dict = await user.save_to_db()
    return user_dict
