"""Modelo ORM para productos del catálogo comercial."""
from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.orm import relationship, synonym

from app.db.database import Base


class Producto(Base):
    """Entidad Producto que refleja los datos comerciales obligatorios según normativa legal."""

    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    descripcion = Column(String(1000), nullable=True)
    precio_final = Column(Numeric(12, 2), nullable=False)
    cuotas_cantidad = Column(Integer, nullable=False, default=1)
    cuotas_valor = Column(Numeric(12, 2), nullable=False, default=0.0)
    garantia_meses = Column(Integer, nullable=False, default=3)
    stock = Column(Integer, nullable=False, default=0)
    imagen_url = Column(String(500), nullable=True)
    categoria = Column(String(100), nullable=True, index=True)

    # Sinónimos para máxima flexibilidad en constructores y consultas
    precio = synonym("precio_final")
    imagen = synonym("imagen_url")

    # Relaciones
    items_pedido = relationship("ItemPedido", back_populates="producto")

