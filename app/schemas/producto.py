"""Esquemas Pydantic para validación y serialización de productos."""
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductoBase(BaseModel):
    """Atributos base requeridos para la exhibición comercial y legal del producto."""

    nombre: str = Field(..., min_length=2, max_length=255, description="Nombre o denominación del producto")
    descripcion: Optional[str] = Field(default=None, description="Descripción técnica y comercial del producto")
    precio_final: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="Precio final al contado en pesos argentinos")
    precio: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="Precio (alias de precio_final)")
    cuotas_cantidad: int = Field(default=1, ge=1, le=60, description="Cantidad de cuotas ofrecidas")
    cuotas_valor: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Valor de cada cuota")
    garantia_meses: int = Field(default=3, ge=0, description="Meses de garantía legal otorgada")
    stock: int = Field(default=0, ge=0, description="Cantidad disponible en inventario")
    categoria: Optional[str] = Field(default=None, max_length=100, description="Categoría temática del producto (ej: Anime, Música, Argentina, Gaming)")
    imagen_url: Optional[str] = Field(default=None, description="URL de imagen del producto")
    imagen: Optional[str] = Field(default=None, description="URL de imagen (alias de imagen_url)")

    @model_validator(mode="before")
    @classmethod
    def sincronizar_alias(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Sincronizar precio y precio_final
            p_final = values.get("precio_final")
            p = values.get("precio")
            if p_final is None and p is not None:
                values["precio_final"] = p
            elif p is None and p_final is not None:
                values["precio"] = p_final

            # Sincronizar imagen e imagen_url
            img_url = values.get("imagen_url")
            img = values.get("imagen")
            if img_url is None and img is not None:
                values["imagen_url"] = img
            elif img is None and img_url is not None:
                values["imagen"] = img_url
        return values

    @model_validator(mode="after")
    def validar_campos(self) -> "ProductoBase":
        if self.precio_final is None and self.precio is None:
            raise ValueError("Debe especificarse el precio del producto ('precio' o 'precio_final').")
        if self.precio_final is None:
            self.precio_final = self.precio
        if self.precio is None:
            self.precio = self.precio_final

        if self.imagen_url is None and self.imagen is not None:
            self.imagen_url = self.imagen
        if self.imagen is None and self.imagen_url is not None:
            self.imagen = self.imagen_url
        return self


class ProductoCreate(ProductoBase):
    """Esquema de entrada para el alta de productos en el catálogo."""
    pass


class ProductoUpdate(BaseModel):
    """Esquema para la actualización parcial o total de productos."""

    nombre: Optional[str] = Field(default=None, min_length=2, max_length=255)
    descripcion: Optional[str] = Field(default=None)
    precio: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="Precio (alias de precio_final)")
    precio_final: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="Precio final al contado")
    cuotas_cantidad: Optional[int] = Field(default=None, ge=1, le=60)
    cuotas_valor: Optional[Decimal] = Field(default=None, ge=Decimal("0.0"))
    garantia_meses: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    categoria: Optional[str] = Field(default=None, max_length=100)
    imagen: Optional[str] = Field(default=None, description="URL de imagen (alias de imagen_url)")
    imagen_url: Optional[str] = Field(default=None, description="URL de imagen del producto")


class ProductoOut(ProductoBase):
    """Esquema de salida con ID asignado e imagen asociada."""

    id: int
    precio_final: Decimal
    precio: Optional[Decimal] = None
    imagen_url: Optional[str] = None
    imagen: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
