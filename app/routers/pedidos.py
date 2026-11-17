"""Endpoints para checkout seguro, consulta de pedidos y botón de arrepentimiento."""
from typing import Union
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.schemas.pedido import (
    CambiarEstadoPedidoIn,
    ItemIn,
    PedidoCreate,
    PedidoOut,
    SolicitudRevocacionOut,
)
from app.services import pedido_service, revocacion_service

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post(
    "",
    response_model=PedidoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo pedido (Checkout seguro)",
    description=(
        "Crea un pedido validando stock, congelando precios y calculando el total en el servidor "
        "de manera atómica. Soporta tanto payload {'items': [...]} como lista directa de ítems."
    ),
)
@router.post(
    "/",
    response_model=PedidoOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def realizar_pedido(
    pedido_in: Union[PedidoCreate, list[ItemIn]],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Pedido:
    """Procesa la orden de compra en una transacción blindada."""
    if isinstance(pedido_in, list):
        pedido_in = PedidoCreate(items=pedido_in)

    return pedido_service.crear_pedido(
        db=db,
        usuario_id=current_user.id,
        datos=pedido_in,
    )


@router.get(
    "",
    response_model=list[PedidoOut],
    summary="Historial de pedidos (Global para Admin / Propios para clientes)",
    description=(
        "Si el usuario es administrador (is_admin == True), retorna todos los pedidos de la tienda "
        "con datos del comprador. Si es un cliente regular, retorna únicamente sus propios pedidos."
    ),
)
@router.get(
    "/",
    response_model=list[PedidoOut],
    include_in_schema=False,
)
@router.get(
    "/todos",
    response_model=list[PedidoOut],
    summary="Historial global de todos los pedidos de la tienda",
    include_in_schema=False,
)
@router.get(
    "/todos/",
    response_model=list[PedidoOut],
    include_in_schema=False,
)
def obtener_pedidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[Pedido]:
    """Retorna todos los pedidos para el Administrador o los pedidos propios para un usuario regular."""
    if current_user.is_admin:
        return pedido_service.obtener_todos_los_pedidos(db=db)
    return pedido_service.obtener_pedidos_usuario(db=db, usuario_id=current_user.id)


@router.get(
    "/mis-pedidos",
    response_model=list[PedidoOut],
    summary="Historial de pedidos del usuario autenticado (alias /mis-pedidos)",
    include_in_schema=False,
)
@router.get(
    "/mis-pedidos/",
    response_model=list[PedidoOut],
    include_in_schema=False,
)
@router.get(
    "/mios",
    response_model=list[PedidoOut],
    summary="Historial de pedidos del usuario autenticado (alias /mios)",
    include_in_schema=False,
)
@router.get(
    "/mios/",
    response_model=list[PedidoOut],
    include_in_schema=False,
)
def mis_pedidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[Pedido]:
    """Retorna las compras propias del usuario actual."""
    return pedido_service.obtener_pedidos_usuario(db=db, usuario_id=current_user.id)


@router.get(
    "/{pedido_id}",
    response_model=PedidoOut,
    summary="Detalle de un pedido",
    description="Retorna el detalle si pertenece al usuario o si el consultante es administrador.",
)
@router.get(
    "/{pedido_id}/",
    response_model=PedidoOut,
    include_in_schema=False,
)
def ver_pedido(
    pedido_id: int = Path(..., description="Identificador único del pedido"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Pedido:
    """Obtiene la información detallada del pedido."""
    return pedido_service.obtener_pedido_por_id(
        db=db,
        pedido_id=pedido_id,
        usuario=current_user,
    )


@router.put(
    "/{pedido_id}/estado",
    response_model=PedidoOut,
    summary="Actualizar estado de un pedido (Sólo Administradores)",
    description=(
        "Endpoint protegido estrictamente con require_admin. Recibe {'nuevo_estado': '...'} "
        "y actualiza el estado del pedido a uno de: 'pendiente', 'aceptado', 'enviado', "
        "'entregado', 'rechazado' o 'cancelado'."
    ),
)
@router.put(
    "/{pedido_id}/estado/",
    response_model=PedidoOut,
    include_in_schema=False,
)
def actualizar_estado_pedido(
    datos: CambiarEstadoPedidoIn,
    pedido_id: int = Path(..., description="Identificador único del pedido"),
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(require_admin),
) -> Pedido:
    """Actualiza el estado del pedido y persiste inmediatamente en SQLite."""
    return pedido_service.actualizar_estado_pedido(
        db=db,
        pedido_id=pedido_id,
        nuevo_estado=datos.nuevo_estado,
    )


@router.post(
    "/{pedido_id}/revocacion",
    response_model=SolicitudRevocacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Botón de Arrepentimiento / Revocación de compra",
    description=(
        "Ejerce el derecho de arrepentimiento según la Ley 24.240 y Disposición 954/2025. "
        "Permite cancelar pedidos dentro de los 10 días corridos de realizada la compra, "
        "reintegrando stock y emitiendo un código de revocación."
    ),
)
@router.post(
    "/{pedido_id}/revocacion/",
    response_model=SolicitudRevocacionOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/{pedido_id}/arrepentimiento",
    response_model=SolicitudRevocacionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Botón de Arrepentimiento (Alias /arrepentimiento)",
    include_in_schema=False,
)
@router.post(
    "/{pedido_id}/arrepentimiento/",
    response_model=SolicitudRevocacionOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def solicitar_revocacion(
    pedido_id: int = Path(..., description="Identificador único del pedido"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> SolicitudRevocacionOut:
    """Registra formalmente la solicitud de revocación y anulación de compra."""
    solicitud = revocacion_service.procesar_revocacion(
        db=db,
        pedido_id=pedido_id,
        usuario=current_user,
    )
    return SolicitudRevocacionOut(
        mensaje="Solicitud de revocación procesada",
        codigo_solicitud=solicitud.codigo,
        estado="cancelado",
        id=solicitud.id,
        codigo=solicitud.codigo,
        pedido_id=solicitud.pedido_id,
        usuario_id=solicitud.usuario_id,
        creada_en=solicitud.creada_en,
    )

