"""Script de inicialización (seeding) para poblar el catálogo de productos y crear el usuario admin.

Rubro: Gimnasio y Equipamiento Deportivo.
Cumplimiento normativo: Ley 24.240 de Defensa del Consumidor (Argentina).

Uso directo:
    cd mi-ecommerce
    python seed.py

Comportamiento:
    - Abre una sesión con SQLAlchemy (SessionLocal).
    - Crea/actualiza el usuario administrador con las credenciales oficiales.
    - Verifica si la tabla 'productos' ya contiene registros.
    - Si contiene datos, no duplica (operación idempotente).
    - Si está vacía, inserta los 4 productos reglamentarios (incluyendo el caso sin imagen).
"""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

# Garantizar que el paquete 'app' sea importable al ejecutar directamente desde la terminal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.database import Base, SessionLocal, engine
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.core.security import hash_password, verificar_password


# ---------------------------------------------------------------------------
# Credenciales del Administrador Oficial
# ---------------------------------------------------------------------------
ADMIN_EMAIL = "bautistabermudez@iresm.edu.ar"
ADMIN_PASSWORD = "48722088"
ADMIN_NOMBRE = "Bautista Bermudez"

# ---------------------------------------------------------------------------
# Catálogo inicial — Gimnasio y Equipamiento Deportivo
# Atributos del modelo SQLAlchemy:
#   - nombre (str)
#   - descripcion (str)
#   - precio_final / precio (Decimal)
#   - cuotas_cantidad (int)
#   - cuotas_valor (Decimal)
#   - garantia_meses (int)
#   - stock (int)
#   - imagen_url / imagen (str o None)
# ---------------------------------------------------------------------------
PRODUCTOS_INICIALES = [
    {
        "nombre": "Par de Mancuernas Hexagonales 10kg",
        "descripcion": "Mancuernas de hierro con recubrimiento en caucho de alta durabilidad y agarre ergonómico antideslizante.",
        "precio_final": Decimal("45000.00"),
        "cuotas_cantidad": 3,
        "cuotas_valor": Decimal("15000.00"),
        "garantia_meses": 6,
        "stock": 15,
        "imagen_url": "https://images.unsplash.com/photo-1638510825316-f346e91ea652?w=500",
    },
    {
        "nombre": "Multiestación Máquina de Poleas y Musculación",
        "descripcion": "Equipo multifunción para entrenamiento completo en casa: pecho, espalda, brazos y piernas.",
        "precio_final": Decimal("380000.00"),
        "cuotas_cantidad": 12,
        "cuotas_valor": Decimal("31666.67"),
        "garantia_meses": 12,
        "stock": 5,
        "imagen_url": "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=500",
    },
    {
        "nombre": "Banco Inclinable Ajustable para Pesas",
        "descripcion": "Banco multiposición reforzado con tapizado de alta densidad para press de banca y mancuernas.",
        "precio_final": Decimal("85000.00"),
        "cuotas_cantidad": 6,
        "cuotas_valor": Decimal("14166.67"),
        "garantia_meses": 6,
        "stock": 8,
        "imagen_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500",
    },
    {
        "nombre": "Straps de Agarre para Peso Muerto",
        "descripcion": "Cintas de algodón reforzado con neopreno para protección de muñeca durante levantamientos pesados.",
        "precio_final": Decimal("12000.00"),
        "cuotas_cantidad": 1,
        "cuotas_valor": Decimal("12000.00"),
        "garantia_meses": 3,
        "stock": 25,
        "imagen_url": None,  # SIN IMAGEN - Obligatorio para entrega de Clase 10
    },
]


# Asegurar encoding UTF-8 en stdout/stderr para entornos Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def seed_admin(db: Session) -> None:
    """Crea o actualiza el usuario administrador oficial.

    - Si el usuario NO existe: lo crea con rol='admin', contraseña hasheada y activo=True.
    - Si el usuario YA existe: actualiza su rol a 'admin' y reaplica la contraseña correcta.
    - Siempre hace db.commit() para persistir en ecommerce.db.
    """
    admin = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()

    if admin is None:
        # ── CREAR usuario admin desde cero ──────────────────────────────
        admin = Usuario(
            nombre=ADMIN_NOMBRE,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            rol="admin",
            acepto_tratamiento=True,
            fecha_consentimiento=datetime.now(timezone.utc),
            activo=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"[ADMIN] ✓ Usuario admin CREADO  → id={admin.id}  email={admin.email}  rol={admin.rol}")
    else:
        # ── ACTUALIZAR usuario existente ─────────────────────────────────
        cambios = []

        if admin.rol != "admin":
            admin.rol = "admin"
            cambios.append("rol → 'admin'")

        # Reaplica la contraseña siempre para garantizar la clave correcta
        if not verificar_password(ADMIN_PASSWORD, admin.hashed_password):
            admin.hashed_password = hash_password(ADMIN_PASSWORD)
            cambios.append("contraseña actualizada")

        if not admin.activo:
            admin.activo = True
            admin.fecha_baja = None
            cambios.append("cuenta reactivada")

        db.commit()
        db.refresh(admin)

        if cambios:
            print(f"[ADMIN] ✓ Usuario admin ACTUALIZADO → id={admin.id}  cambios: {', '.join(cambios)}")
        else:
            print(f"[ADMIN] ✓ Usuario admin ya estaba correcto → id={admin.id}  email={admin.email}  rol={admin.rol}")


def seed_productos(db: Optional[Session] = None) -> int:
    """Inserta el catálogo inicial en la base de datos si la tabla 'productos' está vacía.

    Args:
        db: Sesión SQLAlchemy existente opcional. Si es None, crea una vía SessionLocal.

    Returns:
        int: Cantidad de productos insertados (0 si ya existían datos).
    """
    # Asegura que las tablas existan en SQLite
    Base.metadata.create_all(bind=engine)

    debe_cerrar = False
    if db is None:
        db = SessionLocal()
        debe_cerrar = True

    try:
        # ── 1. Usuario Admin ─────────────────────────────────────────────
        print("\n─── Inicialización del Usuario Administrador ───")
        seed_admin(db)

        # ── 2. Productos ─────────────────────────────────────────────────
        print("\n─── Inicialización del Catálogo de Productos ───")
        total_existentes = db.query(Producto).count()
        if total_existentes > 0:
            print(f"[INFO] La tabla 'productos' ya contiene {total_existentes} registro(s). Se omite el seeding (idempotente).")
            return 0

        print("[SEED] Insertando catálogo inicial de productos (Gimnasio y Equipamiento Deportivo)...")
        for datos in PRODUCTOS_INICIALES:
            producto = Producto(
                nombre=datos["nombre"],
                descripcion=datos.get("descripcion"),
                precio_final=datos.get("precio_final", datos.get("precio")),
                cuotas_cantidad=datos.get("cuotas_cantidad", 1),
                cuotas_valor=datos.get("cuotas_valor", Decimal("0.00")),
                garantia_meses=datos.get("garantia_meses", 3),
                stock=datos["stock"],
                imagen_url=datos.get("imagen_url", datos.get("imagen")),
            )
            db.add(producto)

        db.commit()

        insertados = db.query(Producto).order_by(Producto.id).all()
        print(f"[OK] Se insertaron exitosamente {len(insertados)} productos en 'ecommerce.db':\n")
        print(f"{'ID':<4} | {'Nombre':<45} | {'Precio':<12} | {'Stock':<6} | {'Imagen'}")
        print("-" * 110)
        for p in insertados:
            img = p.imagen_url if p.imagen_url else "[SIN IMAGEN]"
            print(f"{p.id:<4} | {p.nombre:<45} | ${float(p.precio_final):>10,.2f} | {p.stock:<6} | {img}")
        print("-" * 110)

        return len(insertados)

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Error durante la inicialización: {exc}", file=sys.stderr)
        raise
    finally:
        if debe_cerrar:
            db.close()


if __name__ == "__main__":
    seed_productos()
