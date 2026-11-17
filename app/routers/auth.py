"""Endpoints de autenticación, emisión y renovación de credenciales JWT."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.usuario import Usuario
from app.schemas.usuario import RefreshTokenRequest, Token, UsuarioCreate, UsuarioOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea una cuenta validando el consentimiento de privacidad según la Ley 25.326.",
)
def registrar(
    datos_usuario: UsuarioCreate,
    db: Session = Depends(get_db),
) -> Usuario:
    """Registra un nuevo usuario en la plataforma."""
    return auth_service.registrar_usuario(db, datos_usuario)


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión y obtener tokens",
    description="Autentica usuario con formato OAuth2 form (username = email, password).",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Autentica al usuario mediante email y password, entregando un access_token y refresh_token."""
    usuario = auth_service.autenticar_usuario(
        db, email=form_data.username, password=form_data.password
    )
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.generar_par_tokens(usuario)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Renovar access token",
    description="Permite extender la sesión enviando un refresh_token válido.",
)
def refresh(
    solicitud: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Emite un nuevo access token a partir del refresh token válido."""
    return auth_service.refrescar_access_token(db, solicitud.refresh_token)


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Perfil del usuario autenticado",
    description="Obtiene los datos del usuario correspondiente al token Bearer provisto.",
)
def obtener_perfil(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Retorna los datos del perfil activo."""
    return current_user
