from datetime import datetime
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, validator

from .imss_model import IMSS
from .banca_model import Banca
from .empresa_model import Empresa
from .domicilio_model import Domicilio

class TrabajadorBase(BaseModel):
    nombre: str = Field(..., description="Nombre del trabajador")
    apellido_paterno: str = Field(..., description="Apellido paterno del trabajador")
    apellido_materno: str = Field(..., description="Apellido materno del trabajador")
    telefono: str = Field(..., description="Teléfono del trabajador")
    rfc: str = Field(..., description="RFC del trabajador")
    curp: str = Field(..., description="CURP del trabajador")
    domicilio_personal: Domicilio = Field(..., description="Domicilio del trabajador")
    puesto: str = Field(..., description="Puesto del trabajador")
    salario_neto: float = Field(..., description="Salario neto del trabajador")
    salario_bruto: float = Field(..., description="Salario bruto del trabajador")
    actividades: str = Field(..., description="Actividades del trabajador")
    nacionalidad: str = Field(..., description="Nacionalidad del trabajador")
    fecha_nacimiento: datetime = Field(..., description="Fecha de nacimiento del trabajador")
    lugar_nacimiento: str = Field(..., description="Lugar de nacimiento del trabajador")
    edad: int = Field(..., description="Edad del trabajador")
    estado_civil: Literal["Soltero", "Casado", "Divorciado", "Viudo", "Unión libre"] = Field(..., description="Estado civil del trabajador")
    empresa: Empresa = Field(..., description="Empresa del trabajador")
    tiempo_duracion_contrato: int = Field(..., description="Tiempo de duración del contrato en meses")
    sexo: Literal["Masculino", "Femenino", "Otro"] = Field(..., description="Sexo del trabajador")
    tipo_contrato: Literal["Determinado", "Indeterminado", "Por obra determinada", "Periodo de prueba"] = Field(..., description="Tipo de contrato del trabajador")
    fecha_contratacion: datetime = Field(..., description="Fecha de inicio del contrato del trabajador")
    banca: Banca = Field(..., description="Información bancaria del trabajador")
    imss: IMSS = Field(..., description="Número de Seguridad Social del trabajador")
    sd: float = Field(..., description="Salario diario del trabajador")
    factor_integracion: float = Field(..., description="Factor de integración del trabajador")
    empresa_pagadora: str = Field(..., description="Empresa pagadora del trabajador")
    formato_pago: Literal["Semanal", "Quincenal"] = Field(..., description="Formato de pago del trabajador")
    baja : Optional['Baja'] = Field(None, description="Información de baja del trabajador")
    

    class Baja(BaseModel):
        fecha_baja: datetime = Field(..., description="Fecha de baja del trabajador")
        motivo_baja: str = Field(..., description="Motivo de la baja del trabajador")
        observaciones: Optional[str] = Field(None, description="Observaciones adicionales sobre la baja")

    class Config:
        arbitrary_types_allowed = True

class TrabajadorDB(TrabajadorBase):
    id: str = Field(..., description="ID del trabajador (ObjectId de MongoDB)")

    @validator('id')
    def validate_objectid(cls, v):
        if v is not None and not re.fullmatch(r"^[a-fA-F0-9]{24}$", v):
            raise ValueError("El id debe ser un ObjectId válido de MongoDB (24 caracteres hexadecimales)")
        return v

class CreateTrabajador(TrabajadorBase):
    pass

class TrabajadorResponse(TrabajadorBase):
    id: str = Field(..., description="ID del trabajador (ObjectId de MongoDB)")

