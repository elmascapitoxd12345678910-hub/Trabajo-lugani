"""Servicio para el Botón de Arrepentimiento (Ley 24.240 y Disposición 954/2025)."""
import secrets
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pedido import Pedido
from app.models.producto import Producto
from app.models.revocacion import SolicitudRevocacion
from app.models.usuario import Usuario

PLAZO_REVOCACION_DIAS_CORRIDOS = 10


def procesar_revocacion(
    db: Session,
    pedido_id: int,
    usuario: Usuario,
) -> SolicitudRevocacion:
    """Procesa el ejercicio del derecho legal de arrepentimiento/revocación.

    Reglas conforme a la Ley 24.240 y Disposición 954/2025:
      1. El pedido debe existir y pertenecer al usuario autenticado (404).
      2. No debe encontrarse previamente cancelado (409).
      3. No debe poseer una solicitud de revocación previa (409).
      4. Debe solicitarse dentro del plazo perentorio de 10 días corridos desde la compra (400).

    Efectos de la transacción atómica:
      - Reintegro/restauración de stock de cada producto incluido.
      - Modificación del estado del pedido a 'cancelado'.
      - Emisión de un código identificador legible de reclamo: ARR-YYYYMMDD-HEX.
      - Creación del registro en `solicitudes_revocacion`.
    """
    try:
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido or (pedido.usuario_id != usuario.id and not usuario.is_admin):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )

        if pedido.estado == "cancelado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El pedido ya se encuentra cancelado.",
            )

        # Verificar si ya existe una solicitud de revocación registrada
        revocacion_existente = (
            db.query(SolicitudRevocacion)
            .filter(SolicitudRevocacion.pedido_id == pedido.id)
            .first()
        )
        if revocacion_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una solicitud de revocación para este pedido (Código: {revocacion_existente.codigo}).",
            )

        # Validación del plazo legal de 10 días corridos
        ahora_utc = datetime.now(timezone.utc)
        fecha_compra = pedido.creado_en

        # Asegurarse de comparar datetimes con zona horaria UTC
        if fecha_compra.tzinfo is None:
            fecha_compra = fecha_compra.replace(tzinfo=timezone.utc)

        diferencia_tiempo = ahora_utc - fecha_compra
        if diferencia_tiempo.days > PLAZO_REVOCACION_DIAS_CORRIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El plazo legal de {PLAZO_REVOCACION_DIAS_CORRIDOS} días corridos para ejercer "
                    "el derecho de revocación ha expirado conforme a la Ley 24.240."
                ),
            )

        # Restaurar stock de los productos asociados al pedido
        for item in pedido.items:
            producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if producto:
                producto.stock += item.cantidad

        # Actualizar estado del pedido a cancelado
        pedido.estado = "cancelado"

        # Generar código único y formal (REV-2026-XXXXX)
        token_hex = secrets.token_hex(3).upper()[:5]
        codigo_solicitud = f"REV-{ahora_utc.year}-{token_hex}"

        # Registrar la solicitud legal vinculada al pedido y su comprador
        solicitud = SolicitudRevocacion(
            codigo=codigo_solicitud,
            pedido_id=pedido.id,
            usuario_id=pedido.usuario_id,
            creada_en=ahora_utc,
        )

        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)
        db.refresh(pedido)
        return solicitud

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la revocación legal del pedido: {str(exc)}",
        ) from exc
