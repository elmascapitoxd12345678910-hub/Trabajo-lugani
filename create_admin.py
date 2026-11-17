"""Script de creación segura de cuentas administradoras para el e-commerce.

Permite registrar o promover un usuario a Administrador con contraseña hasheada y
persistencia inmediata en SQLite (ecommerce.db).

Uso mediante argumentos CLI:
    python create_admin.py --email admin@tienda.com --nombre "Administrador" --password "AdminPass123!"

Uso interactivo por consola:
    python create_admin.py
"""
import argparse
import getpass
import os
import sys
from datetime import datetime, timezone

# Asegurar que el paquete 'app' esté disponible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.security import hash_password
from app.db.database import Base, SessionLocal, engine
from app.models.usuario import Usuario


def crear_o_actualizar_admin(email: str, nombre: str, password: str) -> Usuario:
    """Crea un usuario administrador o promueve uno existente garantizando hash y rol admin."""
    # Asegurar que las tablas existan en SQLite
    Base.metadata.create_all(bind=engine)

    email = email.strip().lower()
    nombre = nombre.strip()
    if not email or "@" not in email:
        raise ValueError("El email proporcionado no es válido.")
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if not password or len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()

        if usuario:
            print(f"[*] El usuario con email '{email}' ya existe. Promoviendo y actualizando a Administrador...")
            usuario.nombre = nombre
            usuario.hashed_password = hash_password(password)
            usuario.is_admin = True  # Asigna rol = 'admin'
            usuario.activo = True
            usuario.acepto_tratamiento = True
            db.commit()
            db.refresh(usuario)
            print(f"[+] Usuario '{usuario.email}' (ID: {usuario.id}) actualizado exitosamente como Administrador.")
            return usuario
        else:
            print(f"[*] Creando nueva cuenta Administradora para '{email}'...")
            nuevo_admin = Usuario(
                nombre=nombre,
                email=email,
                hashed_password=hash_password(password),
                rol="admin",
                acepto_tratamiento=True,
                fecha_consentimiento=datetime.now(timezone.utc),
                activo=True,
            )
            nuevo_admin.is_admin = True
            db.add(nuevo_admin)
            db.commit()
            db.refresh(nuevo_admin)
            print(f"[+] Administrador '{nuevo_admin.email}' (ID: {nuevo_admin.id}) creado exitosamente en ecommerce.db.")
            return nuevo_admin
    finally:
        db.close()


def main():
    """Punto de entrada de CLI interactivo o con argumentos."""
    parser = argparse.ArgumentParser(
        description="Crear cuenta de Administrador con contraseña hasheada en SQLite."
    )
    parser.add_argument("--email", "-e", type=str, help="Correo electrónico del administrador")
    parser.add_argument("--nombre", "-n", type=str, help="Nombre completo del administrador")
    parser.add_argument("--password", "-p", type=str, help="Contraseña segura en texto plano")

    args = parser.parse_args()

    email = args.email
    nombre = args.nombre
    password = args.password

    # Modo interactivo si falta algún parámetro
    if not email:
        email = input("Ingrese el correo electrónico del administrador: ").strip()
    if not nombre:
        nombre = input("Ingrese el nombre completo del administrador: ").strip()
    if not password:
        try:
            password = getpass.getpass("Ingrese la contraseña del administrador: ")
        except Exception:
            password = input("Ingrese la contraseña del administrador: ")

    try:
        crear_o_actualizar_admin(email=email, nombre=nombre, password=password)
    except Exception as exc:
        print(f"[!] Error al crear la cuenta administradora: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
