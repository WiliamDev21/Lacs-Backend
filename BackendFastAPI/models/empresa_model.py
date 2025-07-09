from pydantic import BaseModel, Field

from .domicilio_model import Domicilio

class Empresa(BaseModel):
    nombre: str = Field(..., description="Nombre de la empresa")
    rfc: str = Field(..., description="RFC de la empresa")
    domicilio: Domicilio = Field(..., description="Domicilio de la empresa")
    giro: str = Field(..., description="Giro de la empresa")
    