"""Utilidades para validación estricta, seguridad y guardado de archivos multimedia."""
import os
import secrets
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

# Extensiones autorizadas
EXTENSIONES_PERMITIDAS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

# Límite máximo de tamaño: 2 Megabytes (2 * 1024 * 1024 bytes)
MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024

# Directorio de almacenamiento dentro de la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "productos"


def parece_imagen(contenido: bytes) -> bool:
    """Verifica si los magic bytes iniciales corresponden a formatos legítimos de imagen.

    Firmas soportadas:
      - JPEG: b"\\xff\\xd8\\xff"
      - PNG:  b"\\x89PNG\\r\\n\\x1a\\n"
      - WEBP: b"RIFF"....b"WEBP"
    """
    if len(contenido) < 12:
        return False

    # Firma JPEG / JPG
    if contenido.startswith(b"\xff\xd8\xff"):
        return True

    # Firma PNG
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    # Firma WEBP (contenedor RIFF)
    if contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP":
        return True

    return False


async def validar_y_guardar_imagen_producto(producto_id: int, file: UploadFile) -> str:
    """Valida y almacena una imagen de producto aplicando las 3 capas de seguridad obligatorias:

    1. Extensión permitida (.jpg, .jpeg, .png, .webp).
    2. Tamaño máximo (< 2 MB -> HTTP 413).
    3. Magic bytes / firma real -> HTTP 415.

    Renombra con UUID/token seguro f"{producto_id}-{secrets.token_hex(8)}{ext}".
    Retorna la URL estática relativa para almacenamiento en Base de Datos.
    """
    # 1. Validación de extensión de archivo
    nombre_original = file.filename or ""
    ext = Path(nombre_original).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extensión '{ext}' no permitida. Solo se aceptan: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}",
        )

    # Lectura del contenido binario
    contenido = await file.read()

    # 2. Validación de tamaño máximo (< 2 MB)
    if len(contenido) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            detail=f"El archivo excede el tamaño máximo permitido de 2 MB (tamaño recibido: {len(contenido) / (1024 * 1024):.2f} MB)",
        )

    # 3. Validación de firma real / magic bytes
    if not parece_imagen(contenido):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El contenido del archivo no corresponde a una imagen válida (magic bytes no reconocidos).",
        )

    # Generación de nombre seguro e impredecible
    token_seguro = secrets.token_hex(8)
    nombre_seguro = f"{producto_id}-{token_seguro}{ext}"

    # Creación del directorio si no existiera
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ruta_destino = UPLOAD_DIR / nombre_seguro

    # Guardado seguro en disco
    with open(ruta_destino, "wb") as f:
        f.write(contenido)

    # Retorna la ruta relativa que se sirve a través del montaje estático /static
    return f"/static/productos/{nombre_seguro}"
