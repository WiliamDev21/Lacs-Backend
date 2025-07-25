from typing import Optional, List
from pydantic import BaseModel, Field


class Asentamiento(BaseModel):
    nombre: str = Field(..., description="Nombre del asentamiento")
    tipo: str = Field(..., description="Tipo de asentamiento (Colonia, Fraccionamiento, etc.)")
    zona: str = Field(..., description="Zona urbana o rural")
    codigo_tipo: str = Field(..., description="Código del tipo de asentamiento")
    id_asentamiento: str = Field(..., description="ID único del asentamiento")


class Ubicacion(BaseModel):
    id: Optional[str] = None
    codigo_postal: str = Field(..., description="Código postal de la ubicación")
    municipio: str = Field(..., description="Municipio de la ubicación")
    estado: str = Field(..., description="Estado de la ubicación")
    ciudad: str = Field(..., description="Ciudad de la ubicación")
    cp_oficina: str = Field(..., description="Código postal de la oficina")
    codigo_estado: str = Field(..., description="Código del estado")
    codigo_oficina: str = Field(..., description="Código de la oficina")
    codigo_cp: str = Field(..., description="Código del CP")
    codigo_municipio: str = Field(..., description="Código del municipio")
    codigo_ciudad: str = Field(..., description="Código de la ciudad")
    asentamientos: List[Asentamiento] = Field(..., description="Lista de asentamientos en la ubicación")