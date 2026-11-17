"""Script de inicialización (seeding) de datos iniciales para producción y demo."""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from app.db.database import Base, SessionLocal, engine
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.core.security import hash_password, verificar_password

STICKERS_DEMO = [
    {
        "nombre": "Sticker Python Developer",
        "descripcion": "Sticker vinilo premium troquelado impermeable de Python.",
        "precio_final": Decimal("1500.00"),
        "cuotas_cantidad": 1,
        "cuotas_valor": Decimal("1500.00"),
        "garantia_meses": 3,
        "stock": 50,
        "imagen_url": "/demo/sticker-python.png",
        "categoria": "Stickers",
    },
    {
        "nombre": "Sticker FastAPI Framework",
        "descripcion": "Sticker holográfico de alta calidad con logo de FastAPI.",
        "precio_final": Decimal("1800.00"),
        "cuotas_cantidad": 1,
        "cuotas_valor": Decimal("1800.00"),
        "garantia_meses": 3,
        "stock": 40,
        "imagen_url": "/demo/sticker-fastapi.png",
        "categoria": "Stickers",
    },
    {
        "nombre": "Sticker Docker Container",
        "descripcion": "Sticker de vinilo resistente al agua de Docker.",
        "precio_final": Decimal("1600.00"),
        "cuotas_cantidad": 1,
        "cuotas_valor": Decimal("1600.00"),
        "garantia_meses": 3,
        "stock": 35,
        "imagen_url": "/demo/sticker-docker.png",
        "categoria": "Stickers",
    },
    {
        "nombre": "Sticker Render Cloud",
        "descripcion": "Sticker acabado mate para laptop de Render Cloud Deploy.",
        "precio_final": Decimal("1700.00"),
        "cuotas_cantidad": 1,
        "cuotas_valor": Decimal("1700.00"),
        "garantia_meses": 3,
        "stock": 30,
        "imagen_url": "/demo/sticker-render.png",
        "categoria": "Stickers",
    },
]


def seed_admin(db: Session) -> Usuario:
    """Crea el usuario administrador si no existe a partir de variables de entorno."""
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@tienda.com").strip().lower()
    password = os.getenv("SEED_ADMIN_PASSWORD", "AdminPass123!")
    nombre = os.getenv("SEED_ADMIN_NOMBRE", "Administrador")

    admin = db.query(Usuario).filter(Usuario.email == email).first()
    if admin is None:
        admin = Usuario(
            nombre=nombre,
            email=email,
            hashed_password=hash_password(password),
            rol="admin",
            acepto_tratamiento=True,
            fecha_consentimiento=datetime.now(timezone.utc),
            activo=True,
        )
        admin.is_admin = True
        db.add(admin)
        db.commit()
        db.refresh(admin)
    else:
        # Asegurar rol admin y estado activo si ya existe
        cambios = False
        if admin.rol != "admin":
            admin.rol = "admin"
            cambios = True
        if not admin.activo:
            admin.activo = True
            cambios = True
        if cambios:
            db.commit()
            db.refresh(admin)

    return admin


def seed_productos(db: Optional[Session] = None) -> int:
    """Inserta los stickers de demo si no existen previamente (idempotente)."""
    debe_cerrar = False
    if db is None:
        db = SessionLocal()
        debe_cerrar = True

    try:
        insertados = 0
        for item in STICKERS_DEMO:
            existente = db.query(Producto).filter(
                (Producto.nombre == item["nombre"]) | (Producto.imagen_url == item["imagen_url"])
            ).first()
            if not existente:
                producto = Producto(
                    nombre=item["nombre"],
                    descripcion=item.get("descripcion"),
                    precio_final=item["precio_final"],
                    cuotas_cantidad=item.get("cuotas_cantidad", 1),
                    cuotas_valor=item.get("cuotas_valor", Decimal("0.00")),
                    garantia_meses=item.get("garantia_meses", 3),
                    stock=item.get("stock", 0),
                    imagen_url=item.get("imagen_url"),
                    categoria=item.get("categoria", "Stickers"),
                )
                db.add(producto)
                insertados += 1

        if insertados > 0:
            db.commit()

        return insertados
    finally:
        if debe_cerrar:
            db.close()


def seed() -> None:
    """Ejecuta el proceso completo de seed."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin(db)
        seed_productos(db)
        print("Seed listo.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

