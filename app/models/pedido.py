"""Modelos ORM para la gestión de pedidos y sus líneas de detalle correspondientes."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def utc_now() -> datetime:
    """Retorna la fecha y hora actual consciente de la zona horaria UTC."""
    return datetime.now(timezone.utc)


class Pedido(Base):
    """Entidad Pedido con congelamiento de total y fecha de transacción."""

    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(String(50), nullable=False, default="pendiente")
    total = Column(Numeric(12, 2), nullable=False, default=0.0)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relaciones
    usuario = relationship("Usuario", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    revocacion = relationship("SolicitudRevocacion", back_populates="pedido", uselist=False)


class ItemPedido(Base):
    """Línea de ítem que congela el precio unitario del producto al momento de la compra."""

    __tablename__ = "items_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)

    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items_pedido")
