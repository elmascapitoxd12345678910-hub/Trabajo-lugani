"""Inyección de dependencias para base de datos y seguridad RBAC."""
from collections.abc import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.db.database import SessionLocal, get_db
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Verifica el token JWT de acceso, recupera el usuario y valida que esté activo."""
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación no válidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_token(token)
        email: str | None = payload.get("sub")
        tipo: str | None = payload.get("tipo")
        if email is None or tipo != "access":
            raise credenciales_exception
    except JWTError:
        raise credenciales_exception

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise credenciales_exception

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta de usuario inactiva o dada de baja",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def require_admin(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Verifica estrictamente que el usuario autenticado posea rol de administrador."""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes: se requiere rol de administrador",
        )
    return current_user
