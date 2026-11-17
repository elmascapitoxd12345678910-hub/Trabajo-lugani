"""Esquemas Pydantic para usuarios, consentimiento informado y autenticación JWT."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator


class UsuarioBase(BaseModel):
    """Atributos base públicos del usuario."""

    nombre: str = Field(..., min_length=2, max_length=255, description="Nombre completo del titular")
    email: EmailStr = Field(..., description="Dirección de correo electrónico válida")


class UsuarioCreate(UsuarioBase):
    """Esquema para registro de nuevos usuarios con consentimiento de tratamiento de datos."""

    password: str = Field(..., min_length=6, max_length=128, description="Contraseña segura en texto plano")
    acepto_tratamiento: bool = Field(
        ...,
        description="Aceptación explícita del tratamiento de datos personales conforme a la Ley 25.326",
    )
    admin_secret: Optional[str] = Field(
        default=None,
        description="Clave secreta opcional para auto-asignar privilegios de administrador",
    )

    @field_validator("acepto_tratamiento")
    @classmethod
    def validar_consentimiento(cls, v: bool) -> bool:
        """Valida estrictamente que el usuario haya consentido el tratamiento de sus datos."""
        if not v:
            raise ValueError(
                "Debe aceptar el tratamiento de datos personales conforme a la Ley 25.326 para registrarse"
            )
        return v


class UsuarioOut(UsuarioBase):
    """Esquema de salida seguro sin hash de contraseñas."""

    id: int
    rol: str
    acepto_tratamiento: bool
    fecha_consentimiento: datetime
    activo: bool
    fecha_baja: Optional[datetime] = None

    @computed_field  # type: ignore[misc]
    @property
    def is_admin(self) -> bool:
        """Expone explícitamente si el usuario tiene permisos de administrador."""
        return self.rol == "admin"

    @computed_field  # type: ignore[misc]
    @property
    def es_admin(self) -> bool:
        """Expone explícitamente si el usuario tiene permisos de administrador (alias en español)."""
        return self.rol == "admin"

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Par de tokens JWT emitidos al autenticarse."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload contenido dentro de los JWT."""

    sub: Optional[str] = None
    rol: Optional[str] = None
    tipo: Optional[str] = None
    exp: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    """Solicitud de renovación de access token mediante refresh token."""

    refresh_token: str


class UsuarioDatosPersonalesOut(BaseModel):
    """Resumen completo de datos almacenados en cumplimiento con el derecho de acceso (Ley 25.326)."""

    usuario: UsuarioOut
    pedidos: list[Any]
    solicitudes_revocacion: list[Any]

    model_config = ConfigDict(from_attributes=True)
