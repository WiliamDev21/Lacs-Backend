from fastapi import APIRouter, HTTPException, status, Depends, Form, Query
from services.database import DatabaseService
from models.user_model import CreateUser, UserResponse
from models.admin_model import Admin
from services.jwt_service import verify_access_token
from fastapi.security import OAuth2PasswordBearer
from utils.credential_generator import generate_user_credentials, generate_admin_credentials
from typing import List, Optional

router = APIRouter(prefix="/admin", tags=["admin"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    
    # Generar credenciales automáticamente
    credentials = generate_user_credentials(nombre, apellido_paterno, apellido_materno)
    
    # Validar que el usuario no exista
    existing = await db.users.find_one({"$or": [{"email": email}, {"nickname": credentials["nickname"]}]})
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe con ese email o nickname.")
    
    # Crear usuario
    user = CreateUser(
        nombre=nombre,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
        nickname=credentials["nickname"],
        password=credentials["password"],
        email=email,
        telefono=telefono,
        rol=rol
    )
    user_dict = await user.save_to_db()
    
    # Retornar las credenciales generadas junto con la información del usuario
    return {
        "user": user_dict,
        "generated_credentials": {
            "nickname": credentials["nickname"],
            "password": credentials["password"]
        }
    }

@router.post("/create-admin", status_code=status.HTTP_200_OK)
async def admin_create_admin(
    nombre: str = Form(...),
    apellido_paterno: str = Form(...),
    apellido_materno: str = Form(...),
    admin_nickname: str = Form(...),
    admin_password: str = Form(...)
):
    db = DatabaseService.get_db()
    # Validar admin como entidad separada
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Generar credenciales para el nuevo admin
    credentials = generate_admin_credentials(nombre, apellido_paterno, apellido_materno)
    
    # Validar que el admin no exista
    existing_admin = await db.admins.find_one({"nickname": credentials["nickname"]})
    if existing_admin:
        raise HTTPException(status_code=400, detail="Ya existe un administrador con ese nickname.")
    
    # Crear nuevo admin
    admin_dict = {
        "nickname": credentials["nickname"],
        "password": Admin.hash_password(credentials["password"]),
        "nombre": nombre,
        "apellido_paterno": apellido_paterno,
        "apellido_materno": apellido_materno
    }
    
    admin_data = await db.admins.insert_one(admin_dict)
    
    if not admin_data:
        raise HTTPException(status_code=500, detail="Error al crear el administrador")
    
    return {
        "message": "Administrador creado exitosamente",
        "generated_credentials": {
            "nickname": credentials["nickname"],
            "password": credentials["password"]
        }
    }

@router.post("/create-first-admin", status_code=status.HTTP_200_OK)
async def create_first_admin(
    nombre: str = Form(...),
    apellido_paterno: str = Form(...),
    apellido_materno: str = Form(...)
):
    """
    Crear el primer administrador del sistema. Solo disponible cuando no hay administradores.
    """
    db = DatabaseService.get_db()
    
    # Verificar que no haya administradores en el sistema
    admin_count = await db.admins.count_documents({})
    if admin_count > 0:
        raise HTTPException(status_code=403, detail="Ya existen administradores en el sistema. Use el endpoint de creación estándar.")
    
    # Generar credenciales para el primer admin
    credentials = generate_admin_credentials(nombre, apellido_paterno, apellido_materno)
    
    # Crear primer admin
    admin_dict = {
        "nickname": credentials["nickname"],
        "password": Admin.hash_password(credentials["password"]),
        "nombre": nombre,
        "apellido_paterno": apellido_paterno,
        "apellido_materno": apellido_materno,
        "es_primer_admin": True
    }
    
    admin_data = await db.admins.insert_one(admin_dict)
    
    if not admin_data:
        raise HTTPException(status_code=500, detail="Error al crear el primer administrador")
    
    return {
        "message": "Primer administrador creado exitosamente",
        "generated_credentials": {
            "nickname": credentials["nickname"],
            "password": credentials["password"]
        },
        "instructions": "Guarde estas credenciales de forma segura. El nickname se usará para autenticar operaciones administrativas."
    }

@router.get("/search-users", response_model=List[UserResponse])
async def search_users(
    admin_nickname: str = Query(..., description="Nickname del administrador"),
    admin_password: str = Query(..., description="Password del administrador"),
    nickname: Optional[str] = Query(None, description="Buscar por nickname"),
    nombre: Optional[str] = Query(None, description="Buscar por nombre"),
    apellido_paterno: Optional[str] = Query(None, description="Buscar por apellido paterno"),
    apellido_materno: Optional[str] = Query(None, description="Buscar por apellido materno"),
    email: Optional[str] = Query(None, description="Buscar por email"),
    telefono: Optional[str] = Query(None, description="Buscar por teléfono"),
    rol: Optional[str] = Query(None, description="Buscar por rol"),
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados"),
    skip: int = Query(0, ge=0, description="Número de resultados a saltar")
):
    """
    Buscar usuarios con diferentes criterios de filtrado.
    Solo administradores pueden acceder a este endpoint.
    """
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Construir filtros de búsqueda
    filters = {}
    if nickname:
        filters["nickname"] = {"$regex": nickname, "$options": "i"}  # Búsqueda insensible a mayúsculas
    if nombre:
        filters["nombre"] = {"$regex": nombre, "$options": "i"}
    if apellido_paterno:
        filters["apellido_paterno"] = {"$regex": apellido_paterno, "$options": "i"}
    if apellido_materno:
        filters["apellido_materno"] = {"$regex": apellido_materno, "$options": "i"}
    if email:
        filters["email"] = {"$regex": email, "$options": "i"}
    if telefono:
        filters["telefono"] = {"$regex": telefono, "$options": "i"}
    if rol:
        filters["rol"] = rol
    
    # Si no hay filtros, devolver error para evitar cargar todos los usuarios
    if not filters:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un criterio de búsqueda")
    
    # Realizar búsqueda
    cursor = db.users.find(filters).skip(skip).limit(limit)
    users = []
    
    async for user_data in cursor:
        # Convertir ObjectId a string
        if "_id" in user_data:
            user_data["id"] = str(user_data.pop("_id"))
        
        # Remover password antes de crear la respuesta
        user_data.pop("password", None)
        
        try:
            user_response = UserResponse(**user_data)
            users.append(user_response)
        except Exception as e:
            # Si hay error en la validación, continuar con el siguiente usuario
            continue
    
    return users

@router.get("/get-user/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    admin_nickname: str = Query(..., description="Nickname del administrador"),
    admin_password: str = Query(..., description="Password del administrador")
):
    """
    Obtener un usuario específico por su ID.
    Solo administradores pueden acceder a este endpoint.
    """
    from bson import ObjectId
    
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Validar formato del ObjectId
    try:
        object_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")
    
    # Buscar usuario
    user_data = await db.users.find_one({"_id": object_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Convertir ObjectId a string y remover password
    user_data["id"] = str(user_data.pop("_id"))
    user_data.pop("password", None)
    
    return UserResponse(**user_data)

@router.post("/change-user-password")
async def admin_change_user_password(
    admin_nickname: str = Form(...),
    admin_password: str = Form(...),
    user_nickname: str = Form(..., description="Nickname del usuario al que cambiar la contraseña"),
    new_password: str = Form(..., description="Nueva contraseña para el usuario")
):
    """
    Cambiar la contraseña de un usuario específico.
    Solo administradores pueden acceder a este endpoint.
    """
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Buscar el usuario
    user_data = await db.users.find_one({"nickname": user_nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Hashear la nueva contraseña
    import hashlib
    import os
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), salt, 100000)
    hashed_new = salt.hex() + ':' + hashed_password.hex()
    
    # Actualizar la contraseña
    result = await db.users.update_one(
        {"nickname": user_nickname}, 
        {"$set": {"password": hashed_new}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Error al actualizar la contraseña")
    
    return {
        "message": f"Contraseña del usuario '{user_nickname}' actualizada correctamente",
        "user_nickname": user_nickname
    }

@router.post("/reset-user-password")
async def admin_reset_user_password(
    admin_nickname: str = Form(...),
    admin_password: str = Form(...),
    user_nickname: str = Form(..., description="Nickname del usuario al que resetear la contraseña")
):
    """
    Resetear la contraseña de un usuario y generar una nueva automáticamente.
    Solo administradores pueden acceder a este endpoint.
    """
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Buscar el usuario
    user_data = await db.users.find_one({"nickname": user_nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Generar nueva contraseña
    from utils.credential_generator import generate_secure_password
    new_password = generate_secure_password()
    
    # Hashear la nueva contraseña
    import hashlib
    import os
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), salt, 100000)
    hashed_new = salt.hex() + ':' + hashed_password.hex()
    
    # Actualizar la contraseña
    result = await db.users.update_one(
        {"nickname": user_nickname}, 
        {"$set": {"password": hashed_new}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Error al resetear la contraseña")
    
    return {
        "message": f"Contraseña del usuario '{user_nickname}' reseteada correctamente",
        "user_nickname": user_nickname,
        "new_password": new_password,
        "instructions": "Proporcione esta nueva contraseña al usuario de forma segura"
    }

@router.put("/update-user/{user_nickname}")
async def admin_update_user(
    user_nickname: str,
    admin_nickname: str = Form(...),
    admin_password: str = Form(...),
    nombre: Optional[str] = Form(None),
    apellido_paterno: Optional[str] = Form(None),
    apellido_materno: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    rol: Optional[str] = Form(None)
):
    """
    Actualizar datos de un usuario específico.
    Solo administradores pueden acceder a este endpoint.
    """
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Buscar el usuario
    user_data = await db.users.find_one({"nickname": user_nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Construir campos a actualizar
    update_fields = {}
    if nombre is not None:
        update_fields["nombre"] = nombre
    if apellido_paterno is not None:
        update_fields["apellido_paterno"] = apellido_paterno
    if apellido_materno is not None:
        update_fields["apellido_materno"] = apellido_materno
    if email is not None:
        # Verificar que el email no esté en uso por otro usuario
        existing_email = await db.users.find_one({"email": email, "nickname": {"$ne": user_nickname}})
        if existing_email:
            raise HTTPException(status_code=400, detail="El email ya está en uso por otro usuario")
        update_fields["email"] = email
    if telefono is not None:
        update_fields["telefono"] = telefono
    if rol is not None:
        update_fields["rol"] = rol
    
    # Verificar que al menos un campo se va a actualizar
    if not update_fields:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un campo para actualizar")
    
    # Actualizar el usuario
    result = await db.users.update_one(
        {"nickname": user_nickname}, 
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Error al actualizar el usuario")
    
    # Obtener los datos actualizados
    updated_user = await db.users.find_one({"nickname": user_nickname})
    if "_id" in updated_user:
        updated_user["id"] = str(updated_user.pop("_id"))
    updated_user.pop("password", None)
    
    return {
        "message": f"Usuario '{user_nickname}' actualizado correctamente",
        "updated_fields": list(update_fields.keys()),
        "user": UserResponse(**updated_user)
    }

@router.delete("/delete-user/{user_nickname}")
async def admin_delete_user(
    user_nickname: str,
    admin_nickname: str = Form(...),
    admin_password: str = Form(...),
    confirm_deletion: bool = Form(..., description="Confirmación de eliminación (debe ser true)")
):
    """
    Eliminar un usuario específico del sistema.
    Solo administradores pueden acceder a este endpoint.
    PRECAUCIÓN: Esta acción es irreversible.
    """
    db = DatabaseService.get_db()
    
    # Validar admin
    admin_data = await db.admins.find_one({"nickname": admin_nickname})
    if not admin_data:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    admin = Admin(admin_data["password"])
    if not admin.verify_password(admin_password):
        raise HTTPException(status_code=401, detail="Contraseña de administrador incorrecta")
    
    # Verificar confirmación
    if not confirm_deletion:
        raise HTTPException(status_code=400, detail="Debe confirmar la eliminación estableciendo confirm_deletion=true")
    
    # Buscar el usuario
    user_data = await db.users.find_one({"nickname": user_nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Guardar información del usuario antes de eliminarlo
    user_info = {
        "nickname": user_data.get("nickname"),
        "nombre": user_data.get("nombre"),
        "apellido_paterno": user_data.get("apellido_paterno"),
        "apellido_materno": user_data.get("apellido_materno"),
        "email": user_data.get("email"),
        "rol": user_data.get("rol")
    }
    
    # Eliminar el usuario
    result = await db.users.delete_one({"nickname": user_nickname})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Error al eliminar el usuario")
    
    return {
        "message": f"Usuario '{user_nickname}' eliminado correctamente",
        "deleted_user_info": user_info,
        "deletion_confirmed_by": admin_nickname,
        "warning": "Esta acción es irreversible"
    }
