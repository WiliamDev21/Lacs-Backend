import datetime
from typing import List
from pydantic import BaseModel, Field

class IMSS(BaseModel):
    nss: str = Field(..., description="Numero de Seguridad Social del trabajador")
    credito_infonavit: bool = Field(..., description="Indica si el trabajador tiene crédito Infonavit")
    numero_credito_infonavit: str = Field(..., description="Número de crédito Infonavit del trabajador")
    registro_patronal: str = Field(..., description="Registro patronal del IMSS")
    fecha_afiliacion: datetime = Field(..., description="Fecha de alta en el IMSS")
    clase_rt: str = Field(..., description="Clase de riesgo del trabajador según el IMSS")
    pensionado: bool = Field(..., description="Indica si el trabajador tiene derecho a pensión")
    pension_alimenticia: bool = Field(..., description="Indica si el trabajador tiene derecho a pensión alimentaria")
    viajero: bool = Field(..., description="Indica si el trabajador es viajero")
    foraneo: bool = Field(..., description="Indica si el trabajador es foráneo")
    maternidad: bool = Field(..., description="Indica si el trabajador tiene derecho a maternidad")
    numero_hijos: int = Field(..., description="Número de hijos del trabajador")
    beneficiarios: List['_Beneficiario'] = Field(..., description="Beneficiarios del trabajador en caso de fallecimiento")
    umf: str = Field(..., description="Unidad médica familiar del IMSS a la que está afiliado el trabajador")
    incapacidad: bool = Field(..., description="Indica si el trabajador tiene derecho a incapacidad")
    sdi: float = Field(..., description="Salario diario integrado del trabajador")

    class Config:
        arbitrary_types_allowed = True


class _Beneficiario(BaseModel):
    nombre: str = Field(..., description="Nombre del beneficiario")
    porcentaje: float = Field(..., description="Porcentaje de la pensión que le corresponde al beneficiario")
    incapacidad: bool = Field(..., description="Indica si el beneficiario tiene derecho a incapacidad")
    tratamiento: bool = Field(..., description="Indica si el beneficiario tiene derecho a tratamiento médico")