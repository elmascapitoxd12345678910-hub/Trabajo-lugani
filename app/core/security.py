"""Utilidades de seguridad, hashing de contraseñas y emisión de JWT."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Contexto de hashing mediante bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera un hash seguro con salt para una contraseña en texto plano."""
    return pwd_context.hash(password)


def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def crear_token(
    data: dict[str, Any],
    tipo: str = "access",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Crea un token JWT firmado (access o refresh) con claims estándar y de expiración.

    Payload generado incluye:
      - sub: identificador del sujeto (email o ID)
      - rol: rol del usuario (ej: 'admin', 'customer')
      - tipo: 'access' o 'refresh'
      - exp: timestamp UTC de expiración
    """
    to_encode = data.copy()

    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        minutos = settings.ACCESS_MIN if tipo == "access" else settings.REFRESH_MIN
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutos)

    to_encode.update({
        "exp": expire,
        "tipo": tipo,
    })

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un token JWT contra la clave secreta y algoritmo configurados.

    Lanza JWTError si el token ha expirado o su firma es inválida.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
