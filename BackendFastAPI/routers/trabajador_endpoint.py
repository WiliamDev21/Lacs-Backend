from fastapi import APIRouter, HTTPException, status, Query, Depends
from services.database import DatabaseService
from models.trabajador_model import TrabajadorDB, CreateTrabajador, TrabajadorResponse
from bson import ObjectId
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer
from services.jwt_service import verify_access_token

router = APIRouter(prefix="/trabajadores", tags=["trabajadores"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return payload

@router.post("/", response_model=TrabajadorResponse, status_code=status.HTTP_201_CREATED)
async def create_trabajador(trabajador: CreateTrabajador, current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    trabajador_dict = trabajador.dict()
    result = await db.trabajadores.insert_one(trabajador_dict)
    trabajador_dict["id"] = str(result.inserted_id)
    return TrabajadorResponse(**trabajador_dict)

@router.get("/{trabajador_id}", response_model=TrabajadorResponse)
async def get_trabajador(trabajador_id: str, current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    data = await db.trabajadores.find_one({"_id": ObjectId(trabajador_id)})
    if not data:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    data["id"] = str(data.pop("_id"))
    return TrabajadorResponse(**data)

@router.put("/{trabajador_id}", response_model=TrabajadorResponse)
async def update_trabajador(trabajador_id: str, trabajador: CreateTrabajador, current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    update_data = {k: v for k, v in trabajador.dict().items() if v is not None}
    result = await db.trabajadores.update_one({"_id": ObjectId(trabajador_id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    data = await db.trabajadores.find_one({"_id": ObjectId(trabajador_id)})
    data["id"] = str(data.pop("_id"))
    return TrabajadorResponse(**data)

@router.delete("/{trabajador_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trabajador(trabajador_id: str, current_user=Depends(get_current_user)):
    db = DatabaseService.get_db()
    result = await db.trabajadores.delete_one({"_id": ObjectId(trabajador_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    return None

@router.get("/", response_model=List[TrabajadorResponse])
async def list_trabajadores(
    nombre: Optional[str] = None,
    apellido_paterno: Optional[str] = None,
    apellido_materno: Optional[str] = None,
    puesto: Optional[str] = None,
    empresa_pagadora: Optional[str] = None,
    sexo: Optional[str] = None,
    tipo_contrato: Optional[str] = None,
    estado_civil: Optional[str] = None,
    nacionalidad: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    db = DatabaseService.get_db()
    filters = {}
    if nombre: filters["nombre"] = nombre
    if apellido_paterno: filters["apellido_paterno"] = apellido_paterno
    if apellido_materno: filters["apellido_materno"] = apellido_materno
    if puesto: filters["puesto"] = puesto
    if empresa_pagadora: filters["empresa_pagadora"] = empresa_pagadora
    if sexo: filters["sexo"] = sexo
    if tipo_contrato: filters["tipo_contrato"] = tipo_contrato
    if estado_civil: filters["estado_civil"] = estado_civil
    if nacionalidad: filters["nacionalidad"] = nacionalidad
    cursor = db.trabajadores.find(filters)
    results = []
    async for data in cursor:
        data["id"] = str(data.pop("_id"))
        results.append(TrabajadorResponse(**data))
    return results

