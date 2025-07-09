from pydantic import BaseModel, Field

class Banca(BaseModel):
    numero_cuenta: str = Field(..., description="Número de cuenta bancaria del trabajador")
    banco: str = Field(..., description="Nombre del banco donde se encuentra la cuenta")
    clabe: str = Field(..., description="CLABE interbancaria de la cuenta")
    