from pydantic import BaseModel, Field

class Domicilio(BaseModel):
    calle: str = Field(..., description="Nombre de la calle")
    numero_exterior: str = Field(..., description="Número exterior del domicilio")
    numero_interior: str = Field(..., description="Número interior del domicilio")
    colonia: str = Field(..., description="Colonia del domicilio")
    codigo_postal: str = Field(..., description="Código postal del domicilio")
    ciudad: str = Field(..., description="Ciudad del domicilio")
    estado: str = Field(..., description="Estado del domicilio")

    def __str__(self):
        return f"{self.calle} {self.numero_exterior}/{self.numero_interior}, {self.colonia}, {self.ciudad}, {self.estado}, {self.codigo_postal}"