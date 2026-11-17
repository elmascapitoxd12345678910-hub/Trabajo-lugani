"""Endpoints para la gestión de usuarios y ejercicio de derechos bajo la Ley 25.326 (LPDP)."""
import json
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.pedido import Pedido
from app.models.revocacion import SolicitudRevocacion
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut
from app.services import auth as auth_service

router = APIRouter(prefix="/usuarios", tags=["Usuarios y Privacidad"])


def recopilar_datos_completos(usuario: Usuario, db: Session) -> dict:
    """Recopila todos los datos personales, comerciales y legales vinculados al usuario."""
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.usuario_id == usuario.id)
        .order_by(Pedido.creado_en.desc())
        .all()
    )

    solicitudes = (
        db.query(SolicitudRevocacion)
        .filter(SolicitudRevocacion.usuario_id == usuario.id)
        .order_by(SolicitudRevocacion.creada_en.desc())
        .all()
    )

    return {
        "titular": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol,
            "activo": usuario.activo,
            "consentimiento_tratamiento_datos": usuario.acepto_tratamiento,
            "fecha_consentimiento": usuario.fecha_consentimiento.isoformat() if usuario.fecha_consentimiento else None,
            "fecha_baja": usuario.fecha_baja.isoformat() if usuario.fecha_baja else None,
        },
        "marco_legal": {
            "normativa_aplicable": "Ley 25.326 de Protección de los Datos Personales (Argentina)",
            "derechos_ejercidos": ["Acceso", "Rectificación", "Supresión/Anonimización"],
        },
        "pedidos": [
            {
                "id": p.id,
                "estado": p.estado,
                "total": float(p.total),
                "creado_en": p.creado_en.isoformat() if p.creado_en else None,
                "items": [
                    {
                        "producto_id": item.producto_id,
                        "cantidad": item.cantidad,
                        "precio_unitario": float(item.precio_unitario),
                    }
                    for item in p.items
                ],
            }
            for p in pedidos
        ],
        "solicitudes_revocacion": [
            {
                "id": s.id,
                "codigo": s.codigo,
                "pedido_id": s.pedido_id,
                "creada_en": s.creada_en.isoformat() if s.creada_en else None,
            }
            for s in solicitudes
        ],
    }


@router.get(
    "/me/datos",
    summary="Consultar todos los datos personales del usuario",
    description=(
        "Ejerce el derecho de acceso contemplado en el Art. 14 de la Ley 25.326. "
        "Devuelve toda la información personal, pedidos, transacciones y consentimientos."
    ),
)
def obtener_mis_datos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Devuelve la totalidad de los datos asociados a la cuenta del usuario."""
    return recopilar_datos_completos(current_user, db)


@router.get(
    "/me/exportar",
    summary="Exportar datos personales en formato JSON descargable",
    description=(
        "Genera un archivo descargable con el header Content-Disposition para que el titular "
        "pueda resguardar o portar sus datos de acuerdo a los estándares de privacidad."
    ),
)
def exportar_mis_datos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Descarga de archivo estructurado de datos personales."""
    datos = recopilar_datos_completos(current_user, db)
    contenido_json = json.dumps(datos, indent=2, ensure_ascii=False)

    filename = f"datos_personales_usuario_{current_user.id}.json"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return Response(
        content=contenido_json,
        media_type="application/json; charset=utf-8",
        headers=headers,
    )


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Baja y anonimización de la cuenta",
    description=(
        "Ejerce el derecho de supresión de la Ley 25.326 sin vulnerar la integridad "
        "referencial ni las obligaciones de preservación contable/fiscal. "
        "Anonimiza nombre, email y contraseña, desactiva la cuenta y marca fecha de baja."
    ),
)
def solicitar_baja_cuenta(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Anonimiza la cuenta del usuario conservando registros fiscales indispensables."""
    # Anonimización sin romper unicidad de email
    token_aleatorio = secrets.token_hex(4)
    current_user.email = f"anon_{current_user.id}_{token_aleatorio}@anonimizado.local"
    current_user.nombre = "Usuario Anonimizado"
    current_user.hashed_password = secrets.token_hex(32)
    current_user.activo = False
    current_user.fecha_baja = datetime.now(timezone.utc)

    db.commit()

    return {
        "status": "success",
        "mensaje": (
            "Su cuenta y datos identificatorios han sido anonimizados y dados de baja exitosamente "
            "en cumplimiento con la Ley 25.326. Los registros de transacciones se conservan de forma disociada "
            "para cumplimiento de deberes tributarios y contables."
        ),
        "fecha_baja": current_user.fecha_baja.isoformat(),
    }


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario (Alias /usuarios)",
    description="Permite registrarse tanto por /auth/register como por /usuarios.",
)
@router.post(
    "/",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def registrar_usuario_alias(
    datos_usuario: UsuarioCreate,
    db: Session = Depends(get_db),
) -> Usuario:
    """Alias para el registro de usuarios."""
    return auth_service.registrar_usuario(db, datos_usuario)
