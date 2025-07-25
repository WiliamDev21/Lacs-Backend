from fastapi import APIRouter, HTTPException, status, Depends, Form, Query
from services.database import DatabaseService
from models.user_model import UserDB, CreateUser, UserResponse
from services.jwt_service import create_access_token, verify_access_token
from fastapi.security import OAuth2PasswordBearer
from utils.credential_generator import generate_user_credentials
from typing import List, Optional

router = APIRouter(prefix="/users", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401, detail="Token inválido o expirado")
    return payload


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    current_user=Depends(get_current_user),
    nombre: str = Form(...),
    apellido_paterno: str = Form(...),
    apellido_materno: str = Form(...),
    email: str = Form(...),
    telefono: str = Form(...),
    rol: str = Form(...)
):
    """
    Crear un nuevo usuario con credenciales generadas automáticamente.
    Solo usuarios con roles administrativos pueden crear usuarios.
    """
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    
    # Solo ciertos roles pueden crear usuarios
    if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"]:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para crear usuarios. Solo Administrador, Inspector, Supervisor o Developer pueden crear usuarios."
        )
    
    # Generar credenciales automáticamente
    credentials = generate_user_credentials(nombre, apellido_paterno, apellido_materno)
    
    # Verificar que el email no esté en uso
    existing_email = await db.users.find_one({"email": email})
    if existing_email:
        raise HTTPException(status_code=400, detail="El email ya está en uso por otro usuario.")
    
    # Verificar que el nickname generado no esté en uso (poco probable pero por seguridad)
    existing_nickname = await db.users.find_one({"nickname": credentials["nickname"]})
    if existing_nickname:
        raise HTTPException(status_code=400, detail="El nickname generado ya está en uso. Intente nuevamente.")
    
    # Crear usuario con credenciales generadas
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
    
    # Guardar el usuario usando el método de la clase
    user_dict = await user.save_to_db()
    
    # Retornar los datos del usuario junto con las credenciales generadas
    return {
        "user": user_dict,
        "generated_credentials": {
            "nickname": credentials["nickname"],
            "password": credentials["password"]
        },
        "message": "Usuario creado exitosamente",
        "instructions": "Proporcione estas credenciales al usuario de forma segura"
    }


@router.post("/change-password")
async def change_password(nickname: str = Form(...), current_password: str = Form(...), new_password: str = Form(...), current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    current_user_nickname = current_user.get("sub", "")
    
    # Los usuarios pueden cambiar su propia contraseña, o los roles administrativos pueden cambiar cualquier contraseña
    if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"] and current_user_nickname != nickname:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para cambiar la contraseña de otro usuario. Solo puedes cambiar tu propia contraseña."
        )
    
    user_data = await db.users.find_one({"nickname": nickname})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = UserDB(**user_data)
    if not user.verify_password(current_password, user.password):
        raise HTTPException(
            status_code=401, detail="Contraseña actual incorrecta")
    # Hashear la nueva contraseña y actualizar
    import hashlib
    import os
    salt = os.urandom(16)
    hashed_password = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), salt, 100000)
    hashed_new = salt.hex() + ':' + hashed_password.hex()
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
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    current_user_nickname = current_user.get("sub", "")
    
    # Los usuarios pueden actualizar sus propios datos, o los roles administrativos pueden actualizar cualquier usuario
    if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"] and current_user_nickname != nickname:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para actualizar los datos de otro usuario. Solo puedes actualizar tus propios datos."
        )
    
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

@router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user=Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    skip: int = Query(0, ge=0, description="Número de resultados a saltar"),
    rol: Optional[str] = Query(None, description="Filtrar por rol"),
    nombre: Optional[str] = Query(None, description="Buscar por nombre (parcial)"),
    nickname: Optional[str] = Query(None, description="Buscar por nickname (parcial)")
):
    """
    Obtener lista de usuarios. Requiere autenticación JWT.
    Solo usuarios con rol 'Administrador', 'Inspector' o 'Supervisor' pueden ver todos los usuarios.
    Otros roles solo pueden ver usuarios con su mismo rol o roles inferiores.
    """
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    
    # Construir filtros de búsqueda
    filters = {}
    
    # Restricciones por rol
    if user_rol in ["Administrador", "Inspector", "Supervisor", "Developer"]:
        # Pueden ver todos los usuarios
        if rol:
            filters["rol"] = rol
    elif user_rol in ["Operador", "Empleado"]:
        # Solo pueden ver usuarios de su mismo rol o roles inferiores
        allowed_roles = ["Operador", "Empleado"]
        if rol and rol in allowed_roles:
            filters["rol"] = rol
        else:
            filters["rol"] = {"$in": allowed_roles}
    else:
        # Rol no reconocido, solo pueden verse a sí mismos
        filters["nickname"] = current_user.get("sub", "")
    
    # Filtros adicionales
    if nombre:
        filters["nombre"] = {"$regex": nombre, "$options": "i"}
    if nickname:
        filters["nickname"] = {"$regex": nickname, "$options": "i"}
    
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

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    """
    Obtener información del usuario autenticado actual.
    """
    db = DatabaseService.get_db()
    
    # Buscar el usuario por nickname
    user_data = await db.users.find_one({"nickname": current_user.get("sub")})
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Convertir ObjectId a string y remover password
    if "_id" in user_data:
        user_data["id"] = str(user_data.pop("_id"))
    user_data.pop("password", None)
    
    return UserResponse(**user_data)

@router.put("/{target_nickname}")
async def update_user(
    target_nickname: str,
    current_user=Depends(get_current_user),
    nombre: Optional[str] = Form(None),
    apellido_paterno: Optional[str] = Form(None),
    apellido_materno: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    rol: Optional[str] = Form(None),
    current_password: str = Form(..., description="Contraseña actual del usuario que realiza la acción")
):
    """
    Actualizar datos de un usuario específico.
    Los usuarios pueden actualizar sus propios datos, o los roles administrativos pueden actualizar cualquier usuario.
    """
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    current_user_nickname = current_user.get("sub", "")
    
    # Los usuarios pueden actualizar sus propios datos, o los roles administrativos pueden actualizar cualquier usuario
    if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"] and current_user_nickname != target_nickname:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para actualizar los datos de otro usuario. Solo puedes actualizar tus propios datos."
        )
    
    # Verificar la contraseña del usuario que realiza la acción
    current_user_data = await db.users.find_one({"nickname": current_user_nickname})
    if not current_user_data:
        raise HTTPException(status_code=404, detail="Usuario actual no encontrado")
    
    current_user_obj = UserDB(**current_user_data)
    if not current_user_obj.verify_password(current_password, current_user_obj.password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    
    # Buscar el usuario objetivo
    target_user_data = await db.users.find_one({"nickname": target_nickname})
    if not target_user_data:
        raise HTTPException(status_code=404, detail="Usuario objetivo no encontrado")
    
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
        existing_email = await db.users.find_one({"email": email, "nickname": {"$ne": target_nickname}})
        if existing_email:
            raise HTTPException(status_code=400, detail="El email ya está en uso por otro usuario")
        update_fields["email"] = email
    if telefono is not None:
        update_fields["telefono"] = telefono
    if rol is not None:
        # Solo roles administrativos pueden cambiar roles
        if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"]:
            raise HTTPException(status_code=403, detail="No tienes permisos para cambiar roles de usuario")
        update_fields["rol"] = rol
    
    # Verificar que al menos un campo se va a actualizar
    if not update_fields:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un campo para actualizar")
    
    # Actualizar el usuario
    result = await db.users.update_one(
        {"nickname": target_nickname}, 
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Error al actualizar el usuario")
    
    # Obtener los datos actualizados
    updated_user = await db.users.find_one({"nickname": target_nickname})
    if "_id" in updated_user:
        updated_user["id"] = str(updated_user.pop("_id"))
    updated_user.pop("password", None)
    
    return {
        "message": f"Usuario '{target_nickname}' actualizado correctamente",
        "updated_fields": list(update_fields.keys()),
        "user": UserResponse(**updated_user)
    }

@router.delete("/{target_nickname}")
async def delete_user(
    target_nickname: str,
    current_user=Depends(get_current_user),
    current_password: str = Form(..., description="Contraseña actual del usuario que realiza la acción"),
    confirm_deletion: bool = Form(..., description="Confirmación de eliminación (debe ser true)")
):
    """
    Eliminar un usuario específico del sistema.
    Solo roles administrativos pueden eliminar usuarios.
    PRECAUCIÓN: Esta acción es irreversible.
    """
    db = DatabaseService.get_db()
    
    # Verificar permisos basados en el rol del usuario actual
    user_rol = current_user.get("rol", "")
    current_user_nickname = current_user.get("sub", "")
    
    # Solo roles administrativos pueden eliminar usuarios
    if user_rol not in ["Administrador", "Inspector", "Supervisor", "Developer"]:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para eliminar usuarios. Solo Administrador, Inspector, Supervisor o Developer pueden eliminar usuarios."
        )
    
    # Verificar confirmación
    if not confirm_deletion:
        raise HTTPException(status_code=400, detail="Debe confirmar la eliminación estableciendo confirm_deletion=true")
    
    # Verificar la contraseña del usuario que realiza la acción
    current_user_data = await db.users.find_one({"nickname": current_user_nickname})
    if not current_user_data:
        raise HTTPException(status_code=404, detail="Usuario actual no encontrado")
    
    current_user_obj = UserDB(**current_user_data)
    if not current_user_obj.verify_password(current_password, current_user_obj.password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    
    # Buscar el usuario objetivo
    target_user_data = await db.users.find_one({"nickname": target_nickname})
    if not target_user_data:
        raise HTTPException(status_code=404, detail="Usuario objetivo no encontrado")
    
    # Prevenir auto-eliminación
    if current_user_nickname == target_nickname:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    
    # Guardar información del usuario antes de eliminarlo
    user_info = {
        "nickname": target_user_data.get("nickname"),
        "nombre": target_user_data.get("nombre"),
        "apellido_paterno": target_user_data.get("apellido_paterno"),
        "apellido_materno": target_user_data.get("apellido_materno"),
        "email": target_user_data.get("email"),
        "rol": target_user_data.get("rol")
    }
    
    # Eliminar el usuario
    result = await db.users.delete_one({"nickname": target_nickname})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Error al eliminar el usuario")
    
    return {
        "message": f"Usuario '{target_nickname}' eliminado correctamente",
        "deleted_user_info": user_info,
        "deletion_performed_by": current_user_nickname,
        "warning": "Esta acción es irreversible"
    }
