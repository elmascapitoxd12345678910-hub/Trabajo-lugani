"""Modelo ORM para el Botón de Arrepentimiento (Ley 24.240 y Disposición 954/2025)."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def utc_now() -> datetime:
    """Retorna la fecha y hora actual consciente de la zona horaria UTC."""
    return datetime.now(timezone.utc)


class SolicitudRevocacion(Base):
    """Registro formal de revocación / arrepentimiento de compra exigido por la normativa argentina."""

    __tablename__ = "solicitudes_revocacion"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(100), unique=True, index=True, nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False, unique=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creada_en = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relaciones
    pedido = relationship("Pedido", back_populates="revocacion")
    usuario = relationship("Usuario", back_populates="revocaciones")
