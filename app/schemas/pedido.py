"""Esquemas Pydantic para checkout, pedidos y derecho de revocación."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ItemIn(BaseModel):
    """Línea de ítem solicitada por el cliente. No admite precios para prevenir manipulaciones."""

    producto_id: Optional[int] = Field(default=None, gt=0, description="Identificador único del producto")
    id: Optional[int] = Field(default=None, gt=0, description="Alias alternativo para ID de producto")
    cantidad: int = Field(default=1, gt=0, description="Cantidad de unidades a comprar")

    @model_validator(mode="after")
    def resolver_producto_id(self):
        if self.producto_id is None:
            if self.id is not None:
                self.producto_id = self.id
            else:
                raise ValueError("Se requiere 'producto_id' o 'id' para el ítem del pedido.")
        return self


class PedidoCreate(BaseModel):
    """Solicitud de creación de pedido. El servidor calcula los totales de forma blindada."""

    items: list[ItemIn] = Field(..., min_length=1, description="Lista de artículos del pedido")



class ItemOut(BaseModel):
    """Detalle de ítem de pedido con precio unitario congelado."""

    id: int
    producto_id: int
    cantidad: int
    precio_unitario: Decimal

    model_config = ConfigDict(from_attributes=True)


class CompradorOut(BaseModel):
    """Datos básicos del comprador para visualización administrativa."""

    id: int
    nombre: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class PedidoOut(BaseModel):
    """Detalle completo del pedido emitido."""

    id: int
    usuario_id: int
    estado: str
    total: Decimal
    creado_en: datetime
    items: list[ItemOut]
    usuario: Optional[CompradorOut] = None
    comprador: Optional[CompradorOut] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sincronizar_comprador(self):
        if self.usuario and not self.comprador:
            self.comprador = self.usuario
        elif self.comprador and not self.usuario:
            self.usuario = self.comprador
        return self


class SolicitudRevocacionOut(BaseModel):
    """Comprobante formal y respuesta del derecho de revocación."""

    mensaje: str = "Solicitud de revocación procesada"
    codigo_solicitud: str
    estado: str = "cancelado"
    id: Optional[int] = None
    codigo: Optional[str] = None
    pedido_id: Optional[int] = None
    usuario_id: Optional[int] = None
    creada_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def sincronizar_codigo(self):
        if not self.codigo_solicitud and self.codigo:
            self.codigo_solicitud = self.codigo
        elif not self.codigo and self.codigo_solicitud:
            self.codigo = self.codigo_solicitud
        return self


ESTADOS_PEDIDO_PERMITIDOS = [
    "pendiente",
    "aceptado",
    "enviado",
    "entregado",
    "rechazado",
    "cancelado",
]


class CambiarEstadoPedidoIn(BaseModel):
    """Cuerpo de solicitud para actualizar el estado del pedido por el Administrador."""

    nuevo_estado: str = Field(..., description="Nuevo estado del pedido")

    @field_validator("nuevo_estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        estado_clean = v.strip().lower()
        if estado_clean not in ESTADOS_PEDIDO_PERMITIDOS:
            raise ValueError(
                f"Estado '{v}' no permitido. Valores permitidos: {', '.join(ESTADOS_PEDIDO_PERMITIDOS)}"
            )
        return estado_clean
