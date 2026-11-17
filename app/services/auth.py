"""Servicio de autenticación, registro y gestión de tokens."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import crear_token, decodificar_token, hash_password, verificar_password
from app.models.usuario import Usuario
from app.schemas.usuario import Token, UsuarioCreate


def obtener_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    """Obtiene un usuario por su dirección de email."""
    return db.query(Usuario).filter(Usuario.email == email).first()


def registrar_usuario(db: Session, datos: UsuarioCreate) -> Usuario:
    """Registra un nuevo usuario en el sistema garantizando la unicidad de email y el consentimiento."""
    usuario_existente = obtener_usuario_por_email(db, datos.email)
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con este correo electrónico",
        )

    es_admin = bool(datos.admin_secret and datos.admin_secret == settings.ADMIN_SECRET_KEY)

    nuevo_usuario = Usuario(
        nombre=datos.nombre,
        email=datos.email,
        hashed_password=hash_password(datos.password),
        rol="admin" if es_admin else "customer",
        acepto_tratamiento=datos.acepto_tratamiento,
        fecha_consentimiento=datetime.now(timezone.utc),
        activo=True,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


def autenticar_usuario(db: Session, email: str, password: str) -> Optional[Usuario]:
    """Valida las credenciales de acceso del usuario y su estado activo."""
    usuario = obtener_usuario_por_email(db, email)
    if not usuario:
        return None
    if not verificar_password(password, usuario.hashed_password):
        return None
    if not usuario.activo:
        return None
    return usuario


def generar_par_tokens(usuario: Usuario) -> Token:
    """Genera access token y refresh token para el usuario autenticado."""
    payload = {
        "sub": usuario.email,
        "rol": usuario.rol,
    }
    access_token = crear_token(payload, tipo="access")
    refresh_token = crear_token(payload, tipo="refresh")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


def refrescar_access_token(db: Session, refresh_token: str) -> Token:
    """Valida el refresh token y emite un nuevo access token manteniendo el refresh token."""
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_token(refresh_token)
        email: str | None = payload.get("sub")
        tipo: str | None = payload.get("tipo")
        if email is None or tipo != "refresh":
            raise credenciales_exception
    except Exception:
        raise credenciales_exception

    usuario = obtener_usuario_por_email(db, email)
    if not usuario or not usuario.activo:
        raise credenciales_exception

    nuevo_payload = {
        "sub": usuario.email,
        "rol": usuario.rol,
    }
    nuevo_access_token = crear_token(nuevo_payload, tipo="access")

    return Token(
        access_token=nuevo_access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
