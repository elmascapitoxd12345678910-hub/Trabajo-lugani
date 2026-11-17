"""Endpoints para la gestión y consulta del catálogo de productos e imágenes."""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.producto import ProductoCreate, ProductoOut, ProductoUpdate
from app.services import productos as producto_service
from app.utils.archivos import validar_y_guardar_imagen_producto

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get(
    "",
    response_model=list[ProductoOut],
    summary="Listar catálogo de productos",
    description="Obtiene los productos con paginación y filtros opcionales de búsqueda.",
)
@router.get(
    "/",
    response_model=list[ProductoOut],
    include_in_schema=False,
)
def listar_productos(
    page: int = Query(default=0, ge=0, description="Número de página (base 0). Alternativa a skip."),
    skip: int = Query(default=0, ge=0, description="Cantidad de registros a omitir (alternativa a page)"),
    limit: int = Query(default=12, ge=1, le=100, description="Cantidad máxima a retornar"),
    nombre: Optional[str] = Query(default=None, description="Filtro por coincidencia de nombre"),
    categoria: Optional[str] = Query(default=None, description="Filtro por categoría temática (e.g. Gaming, Anime, Música, Argentina)"),
    precio_max: Optional[Decimal] = Query(default=None, ge=Decimal("0.0"), description="Filtro por precio tope"),
    db: Session = Depends(get_db),
) -> list[Producto]:
    """Retorna la lista de productos filtrada y paginada.

    Acepta tanto `page` (base 0, estilo frontend) como `skip` (offset directo).
    Si se envía `page`, el offset real se calcula como page * limit.
    """
    # Compatibilidad: page toma precedencia sobre skip cuando es > 0
    offset = page * limit if page > 0 else skip
    return producto_service.listar_productos(
        db=db, skip=offset, limit=limit, nombre=nombre, categoria=categoria, precio_max=precio_max
    )


@router.get(
    "/{id}",
    response_model=ProductoOut,
    summary="Obtener detalle de un producto",
    description="Retorna la ficha técnica y comercial del producto.",
)
@router.get(
    "/{id}/",
    response_model=ProductoOut,
    include_in_schema=False,
)
def obtener_producto(
    id: int,
    db: Session = Depends(get_db),
) -> Producto:
    """Busca y retorna un producto por su ID."""
    producto = producto_service.obtener_producto_por_id(db, id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return producto


@router.post(
    "",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto",
    description="Exclusivo administradores. Registra un nuevo producto comercial.",
)
@router.post(
    "/",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def crear_producto(
    datos_producto: ProductoCreate,
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(require_admin),
) -> Producto:
    """Crea un producto en el catálogo previa autorización como admin."""
    return producto_service.crear_producto(db, datos_producto)


@router.put(
    "/{id}",
    response_model=ProductoOut,
    summary="Actualizar producto existente",
    description="Exclusivo administradores. Modifica atributos de un producto.",
)
@router.put(
    "/{id}/",
    response_model=ProductoOut,
    include_in_schema=False,
)
@router.patch(
    "/{id}",
    response_model=ProductoOut,
    summary="Actualizar parcialmente un producto existente (PATCH)",
    description="Exclusivo administradores. Modifica atributos de un producto de forma parcial o total.",
)
@router.patch(
    "/{id}/",
    response_model=ProductoOut,
    include_in_schema=False,
)
def actualizar_producto(
    id: int,
    datos_producto: ProductoUpdate,
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(require_admin),
) -> Producto:
    """Actualiza los datos del producto especificado."""
    producto_actualizado = producto_service.actualizar_producto(db, id, datos_producto)
    if not producto_actualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return producto_actualizado


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar producto",
    description="Exclusivo administradores. Da de baja un producto del catálogo.",
)
@router.delete(
    "/{id}/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def eliminar_producto(
    id: int,
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(require_admin),
) -> dict[str, str]:
    """Elimina permanentemente un producto del catálogo."""
    eliminado = producto_service.eliminar_producto(db, id)
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return {"mensaje": "Producto eliminado exitosamente"}


@router.post(
    "/{id}/imagen",
    response_model=ProductoOut,
    summary="Subir imagen de producto",
    description=(
        "Exclusivo administradores. Sube y valida la imagen en 3 capas: "
        "extensión permitida, tamaño menor a 2MB y firma/magic bytes real."
    ),
)
@router.post(
    "/{id}/imagen/",
    response_model=ProductoOut,
    include_in_schema=False,
)
async def subir_imagen_producto(
    id: int,
    archivo: UploadFile = File(..., description="Archivo de imagen (.jpg, .png, .webp)"),
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(require_admin),
) -> Producto:
    """Valida exhaustivamente y almacena la imagen del producto."""
    producto = producto_service.obtener_producto_por_id(db, id)
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    # Validación y guardado en 3 capas de seguridad
    imagen_url = await validar_y_guardar_imagen_producto(producto_id=id, file=archivo)

    # Actualización del registro en la base de datos
    producto_actualizado = producto_service.actualizar_imagen_producto(db, id, imagen_url)
    return producto_actualizado
