"""Servicio transaccional para pedidos, control de inventario y congelamiento de precios."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.pedido import ItemPedido, Pedido
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.pedido import PedidoCreate


def crear_pedido(db: Session, usuario_id: int, datos: PedidoCreate) -> Pedido:
    """Crea un pedido realizando el cálculo de precios y descuento de stock en una transacción atómica.

    Garantiza:
      1. Verificación de existencia del producto (404).
      2. Verificación de stock disponible (409 ante stock insuficiente).
      3. Descuento inmediato de inventario.
      4. Congelamiento del precio unitario al momento exacto de la compra.
      5. Cálculo del importe total únicamente en el servidor (anti-fraude).
      6. Rollback total ante cualquier falla de integridad.
    """
    total_acumulado = Decimal("0.00")
    items_a_crear: list[ItemPedido] = []

    # Se inicia el bloque atómico
    try:
        for item_in in datos.items:
            # Bloqueo o consulta del producto
            producto = db.query(Producto).filter(Producto.id == item_in.producto_id).first()
            if not producto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El producto con ID {item_in.producto_id} no fue encontrado en el catálogo.",
                )

            # Validación de stock suficiente
            if producto.stock < item_in.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Stock insuficiente para el producto '{producto.nombre}'. "
                        f"Disponible: {producto.stock}, Solicitado: {item_in.cantidad}."
                    ),
                )

            # Descuento de stock en la base de datos
            producto.stock -= item_in.cantidad

            # Congelamiento del precio unitario actual
            precio_unitario = Decimal(str(producto.precio_final))
            subtotal = precio_unitario * Decimal(item_in.cantidad)
            total_acumulado += subtotal

            # Creación de la línea de ítem
            item_db = ItemPedido(
                producto_id=producto.id,
                cantidad=item_in.cantidad,
                precio_unitario=precio_unitario,
            )
            items_a_crear.append(item_db)

        # Creación del pedido con total calculado por el servidor
        nuevo_pedido = Pedido(
            usuario_id=usuario_id,
            estado="pendiente",
            total=total_acumulado,
            creado_en=datetime.now(timezone.utc),
            items=items_a_crear,
        )

        db.add(nuevo_pedido)
        db.commit()
        db.refresh(nuevo_pedido)
        return nuevo_pedido

    except HTTPException:
        # Revertir cualquier cambio previo en la sesión ante validación de negocio fallida
        db.rollback()
        raise
    except Exception as exc:
        # Revertir cualquier fallo no previsto de base de datos
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno durante la transacción del pedido: {str(exc)}",
        ) from exc


def obtener_pedidos_usuario(db: Session, usuario_id: int) -> list[Pedido]:
    """Retorna el historial completo de pedidos del usuario, del más reciente al más antiguo."""
    return (
        db.query(Pedido)
        .filter(Pedido.usuario_id == usuario_id)
        .order_by(Pedido.creado_en.desc())
        .all()
    )


def obtener_pedido_por_id(db: Session, pedido_id: int, usuario: Usuario) -> Pedido:
    """Retorna el detalle del pedido si pertenece al usuario o si el solicitante es administrador.

    Lanza HTTP 404 si el pedido no existe o es ajeno, protegiendo la privacidad de los pedidos.
    """
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    # Si no es admin y no es el dueño, se retorna 404 por seguridad
    if pedido.usuario_id != usuario.id and not usuario.is_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    return pedido


def obtener_todos_los_pedidos(db: Session) -> list[Pedido]:
    """Retorna la lista de todos los pedidos realizados en la tienda, del más reciente al más antiguo."""
    return db.query(Pedido).order_by(Pedido.creado_en.desc()).all()


def actualizar_estado_pedido(db: Session, pedido_id: int, nuevo_estado: str) -> Pedido:
    """Actualiza el estado de un pedido y persiste de inmediato en la base de datos."""
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    pedido.estado = nuevo_estado
    db.commit()
    db.refresh(pedido)
    return pedido

