"""Servicio de lógica de negocio para productos del catálogo."""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.schemas.producto import ProductoCreate, ProductoUpdate


def listar_productos(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    nombre: Optional[str] = None,
    categoria: Optional[str] = None,
    precio_max: Optional[Decimal] = None,
) -> list[Producto]:
    """Obtiene la lista de productos con paginación y filtros opcionales."""
    query = db.query(Producto)

    if nombre:
        query = query.filter(Producto.nombre.ilike(f"%{nombre}%"))
    if categoria:
        query = query.filter(Producto.categoria.ilike(f"%{categoria}%"))
    if precio_max is not None:
        query = query.filter(Producto.precio_final <= precio_max)

    return query.offset(skip).limit(limit).all()


def obtener_producto_por_id(db: Session, producto_id: int) -> Optional[Producto]:
    """Busca un producto por su clave primaria."""
    return db.query(Producto).filter(Producto.id == producto_id).first()


def crear_producto(db: Session, datos: ProductoCreate) -> Producto:
    """Registra un nuevo producto en la base de datos y garantiza su persistencia."""
    precio_a_guardar = datos.precio_final if datos.precio_final is not None else datos.precio
    imagen_a_guardar = datos.imagen_url or datos.imagen

    # Cálculo automático de cuotas_valor si no se envió o es 0 pero hay cuotas > 1
    cuotas_val = datos.cuotas_valor
    if (cuotas_val is None or cuotas_val == Decimal("0.0")) and datos.cuotas_cantidad and datos.cuotas_cantidad > 1 and precio_a_guardar:
        cuotas_val = round(precio_a_guardar / datos.cuotas_cantidad, 2)
    elif cuotas_val is None:
        cuotas_val = Decimal("0.0")

    db_producto = Producto(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        precio_final=precio_a_guardar,
        cuotas_cantidad=datos.cuotas_cantidad or 1,
        cuotas_valor=cuotas_val,
        garantia_meses=datos.garantia_meses if datos.garantia_meses is not None else 3,
        stock=datos.stock if datos.stock is not None else 0,
        imagen_url=imagen_a_guardar,
        categoria=datos.categoria,
    )
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


def actualizar_producto(
    db: Session, producto_id: int, datos: ProductoUpdate
) -> Optional[Producto]:
    """Actualiza los campos provistos de un producto existente."""
    producto = obtener_producto_por_id(db, producto_id)
    if not producto:
        return None

    update_data = datos.model_dump(exclude_unset=True)

    # Normalizar alias de precio -> precio_final
    if "precio" in update_data:
        val = update_data.pop("precio")
        if "precio_final" not in update_data:
            update_data["precio_final"] = val

    # Normalizar alias de imagen -> imagen_url
    if "imagen" in update_data:
        val = update_data.pop("imagen")
        if "imagen_url" not in update_data:
            update_data["imagen_url"] = val

    for key, value in update_data.items():
        setattr(producto, key, value)

    db.commit()
    db.refresh(producto)
    return producto


def eliminar_producto(db: Session, producto_id: int) -> bool:
    """Elimina un producto del catálogo."""
    producto = obtener_producto_por_id(db, producto_id)
    if not producto:
        return False

    db.delete(producto)
    db.commit()
    return True


def actualizar_imagen_producto(
    db: Session, producto_id: int, imagen_url: str
) -> Optional[Producto]:
    """Asocia la URL de la imagen guardada al producto."""
    producto = obtener_producto_por_id(db, producto_id)
    if not producto:
        return None

    producto.imagen_url = imagen_url
    db.commit()
    db.refresh(producto)
    return producto
