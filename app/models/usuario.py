"""Modelo ORM para usuarios y gestión de consentimientos de privacidad."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def utc_now() -> datetime:
    """Retorna la fecha y hora actual consciente de la zona horaria UTC."""
    return datetime.now(timezone.utc)


class Usuario(Base):
    """Entidad Usuario para autenticación y cumplimiento de la Ley 25.326 de Protección de Datos Personales."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False, default="customer")
    acepto_tratamiento = Column(Boolean, nullable=False, default=False)
    fecha_consentimiento = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_baja = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    pedidos = relationship("Pedido", back_populates="usuario")
    revocaciones = relationship("SolicitudRevocacion", back_populates="usuario")

    @property
    def is_admin(self) -> bool:
        """Determina si el usuario posee rol de administrador."""
        return self.rol == "admin"

    @is_admin.setter
    def is_admin(self, value: bool) -> None:
        self.rol = "admin" if value else "customer"

    @property
    def es_admin(self) -> bool:
        """Alias en español para compatibilidad total con is_admin."""
        return self.is_admin

    @es_admin.setter
    def es_admin(self, value: bool) -> None:
        self.is_admin = value
