"""Suite de pruebas de integración completa para validar todas las capas y normativas legales."""
import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.usuario import Usuario

# Base de datos SQLite en memoria para tests aislados y rápidos
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Crear tablas en memoria
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_01_root_endpoint():
    """Valida endpoint raíz y mención legal."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "Ley 24.240" in data["normativa"]


def test_02_register_consentimiento_obligatorio():
    """Verifica el rechazo si no se consiente el tratamiento de datos (Ley 25.326)."""
    res = client.post(
        "/auth/register",
        json={
            "nombre": "Juan Pérez",
            "email": "juan@ejemplo.com",
            "password": "Password123!",
            "acepto_tratamiento": False,
        },
    )
    # Pydantic debe rechazar con 422 Unprocessable Entity
    assert res.status_code == 422


def test_03_register_exitoso_y_duplicado():
    """Registra usuario con consentimiento y previene duplicación."""
    res = client.post(
        "/auth/register",
        json={
            "nombre": "Juan Pérez",
            "email": "juan@ejemplo.com",
            "password": "Password123!",
            "acepto_tratamiento": True,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "juan@ejemplo.com"
    assert data["acepto_tratamiento"] is True
    assert "password" not in data
    assert "hashed_password" not in data

    # Intento de registrar con el mismo email -> 400
    res_dup = client.post(
        "/auth/register",
        json={
            "nombre": "Juan Clon",
            "email": "juan@ejemplo.com",
            "password": "Password123!",
            "acepto_tratamiento": True,
        },
    )
    assert res_dup.status_code == 400


def test_04_login_y_tokens():
    """Prueba autenticación OAuth2 y refresco de tokens."""
    # Login fallido
    res_fail = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "WrongPassword"},
    )
    assert res_fail.status_code == 401

    # Login exitoso
    res = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "Password123!"},
    )
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Perfil /auth/me
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    res_me = client.get("/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "juan@ejemplo.com"

    # Refresh token
    res_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert res_refresh.status_code == 200
    assert "access_token" in res_refresh.json()


def test_05_rbac_administrador_y_productos():
    """Valida que solo administradores puedan crear y modificar productos."""
    # Login de Juan (customer)
    res_login = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "Password123!"},
    )
    cust_token = res_login.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {cust_token}"}

    # Crear producto siendo cliente -> 403 Forbidden
    nuevo_prod_data = {
        "nombre": "Smart TV 55 Pulgadas 4K",
        "precio_final": 500000.0,
        "cuotas_cantidad": 12,
        "cuotas_valor": 45000.0,
        "garantia_meses": 12,
        "stock": 10,
    }
    res_cust_prod = client.post("/productos/", json=nuevo_prod_data, headers=cust_headers)
    assert res_cust_prod.status_code == 403

    # Crear un usuario administrador en la base de datos
    db = TestingSessionLocal()
    admin_user = Usuario(
        nombre="Admin E-Commerce",
        email="admin@tienda.com",
        hashed_password="hashed_admin_password",
        rol="admin",
        acepto_tratamiento=True,
        activo=True,
    )
    from app.core.security import hash_password
    admin_user.hashed_password = hash_password("AdminSecret123!")
    db.add(admin_user)
    db.commit()
    db.close()

    # Login como admin
    res_admin_login = client.post(
        "/auth/login",
        data={"username": "admin@tienda.com", "password": "AdminSecret123!"},
    )
    admin_token = res_admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Crear producto como admin -> 201 Created
    res_prod = client.post("/productos/", json=nuevo_prod_data, headers=admin_headers)
    assert res_prod.status_code == 201
    prod_data = res_prod.json()
    assert prod_data["id"] == 1
    assert prod_data["stock"] == 10

    # Actualizar producto como admin -> 200 OK
    res_update = client.put(
        "/productos/1",
        json={"precio_final": 480000.0, "stock": 5},
        headers=admin_headers,
    )
    assert res_update.status_code == 200
    assert float(res_update.json()["precio_final"]) == 480000.0
    assert res_update.json()["stock"] == 5


def test_06_subida_de_imagenes_seguridad():
    """Valida las 3 capas de seguridad en la subida de imágenes."""
    # Login admin
    res_login = client.post(
        "/auth/login",
        data={"username": "admin@tienda.com", "password": "AdminSecret123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # 1. Extensión prohibida (.exe) -> 415
    archivo_falso = io.BytesIO(b"malware content")
    res_ext = client.post(
        "/productos/1/imagen",
        files={"archivo": ("virus.exe", archivo_falso, "application/octet-stream")},
        headers=admin_headers,
    )
    assert res_ext.status_code == 415

    # 2. Tamaño excesivo (> 2 MB) -> 413
    archivo_gigante = io.BytesIO(b"0" * (2 * 1024 * 1024 + 10))
    res_size = client.post(
        "/productos/1/imagen",
        files={"archivo": ("foto_pesada.png", archivo_gigante, "image/png")},
        headers=admin_headers,
    )
    assert res_size.status_code == 413

    # 3. Firma / Magic bytes falsos (archivo .png con contenido de texto) -> 415
    archivo_falso_png = io.BytesIO(b"Este texto no es un PNG real ni tiene magic bytes")
    res_magic = client.post(
        "/productos/1/imagen",
        files={"archivo": ("falsa_foto.png", archivo_falso_png, "image/png")},
        headers=admin_headers,
    )
    assert res_magic.status_code == 415

    # 4. Imagen legítima con firma PNG (b"\x89PNG\r\n\x1a\n" ...) -> 200 OK
    png_valido = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    archivo_valido = io.BytesIO(png_valido)
    res_ok = client.post(
        "/productos/1/imagen",
        files={"archivo": ("foto_real.png", archivo_valido, "image/png")},
        headers=admin_headers,
    )
    assert res_ok.status_code == 200
    data_imagen = res_ok.json()
    assert data_imagen["imagen_url"] is not None
    assert "/static/productos/1-" in data_imagen["imagen_url"]


def test_07_checkout_transaccional_y_control_stock():
    """Valida checkout atómico, descuento de stock y congelamiento de precios."""
    # Login cliente
    res_login = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # Stock actual del producto 1 es 5.
    # Pedir 10 unidades -> 409 Conflict por stock insuficiente
    res_fail_order = client.post(
        "/pedidos/",
        json={"items": [{"producto_id": 1, "cantidad": 10}]},
        headers=cust_headers,
    )
    assert res_fail_order.status_code == 409
    assert "Stock insuficiente" in res_fail_order.json()["detail"]

    # Verificar que el stock sigue siendo 5 (garantía de rollback)
    res_check_prod = client.get("/productos/1")
    assert res_check_prod.json()["stock"] == 5

    # Comprar 2 unidades legítimas -> 201 Created
    # Precio unitario actual: 480000.0 * 2 = 960000.0
    res_order = client.post(
        "/pedidos/",
        json={"items": [{"producto_id": 1, "cantidad": 2}]},
        headers=cust_headers,
    )
    assert res_order.status_code == 201
    order_data = res_order.json()
    assert order_data["id"] == 1
    assert float(order_data["total"]) == 960000.0
    assert len(order_data["items"]) == 1
    assert float(order_data["items"][0]["precio_unitario"]) == 480000.0

    # Verificar que el stock disminuyó de 5 a 3
    res_prod_after = client.get("/productos/1")
    assert res_prod_after.json()["stock"] == 3

    # Verificar historial en /pedidos/mios
    res_mios = client.get("/pedidos/mios", headers=cust_headers)
    assert res_mios.status_code == 200
    assert len(res_mios.json()) == 1


def test_08_boton_arrepentimiento_ley_24240():
    """Valida el ejercicio del derecho de revocación según Ley 24.240 y Disposición 954/2025."""
    # Login cliente
    res_login = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # Revocar el pedido 1
    res_revoc = client.post("/pedidos/1/revocacion", headers=cust_headers)
    assert res_revoc.status_code == 201
    revoc_data = res_revoc.json()
    assert revoc_data["codigo"].startswith(("ARR-", "REV-"))
    assert revoc_data["codigo_solicitud"].startswith(("ARR-", "REV-"))
    assert revoc_data["estado"] == "cancelado"
    assert revoc_data["pedido_id"] == 1

    # Verificar que el stock se restauró de 3 a 5
    res_prod = client.get("/productos/1")
    assert res_prod.json()["stock"] == 5

    # Verificar que el pedido ahora tiene estado "cancelado"
    res_order = client.get("/pedidos/1", headers=cust_headers)
    assert res_order.json()["estado"] == "cancelado"

    # Intentar revocar nuevamente -> 409 Conflict
    res_revoc_dup = client.post("/pedidos/1/revocacion", headers=cust_headers)
    assert res_revoc_dup.status_code == 409


def test_09_proteccion_datos_personales_ley_25326():
    """Valida derechos de acceso, exportación y anonimización/supresión."""
    # Login cliente
    res_login = client.post(
        "/auth/login",
        data={"username": "juan@ejemplo.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # 1. Derecho de Acceso: /usuarios/me/datos
    res_datos = client.get("/usuarios/me/datos", headers=cust_headers)
    assert res_datos.status_code == 200
    datos = res_datos.json()
    assert datos["titular"]["email"] == "juan@ejemplo.com"
    assert len(datos["pedidos"]) == 1
    assert len(datos["solicitudes_revocacion"]) == 1

    # 2. Portabilidad / Exportación: /usuarios/me/exportar
    res_export = client.get("/usuarios/me/exportar", headers=cust_headers)
    assert res_export.status_code == 200
    assert "attachment; filename=" in res_export.headers.get("content-disposition", "")
    assert b"juan@ejemplo.com" in res_export.content

    # 3. Supresión / Anonimización: DELETE /usuarios/me
    res_delete = client.delete("/usuarios/me", headers=cust_headers)
    assert res_delete.status_code == 200
    assert "anonimizados y dados de baja exitosamente" in res_delete.json()["mensaje"]

    # 4. Verificar que la cuenta queda inactiva y no puede operar
    res_me_inactivo = client.get("/auth/me", headers=cust_headers)
    assert res_me_inactivo.status_code == 401

    # 5. Verificar que el pedido se conserva para registro contable
    db = TestingSessionLocal()
    from app.models.pedido import Pedido
    pedido_conservado = db.query(Pedido).filter(Pedido.id == 1).first()
    assert pedido_conservado is not None
    assert pedido_conservado.usuario_id == 1
    # Y el usuario existe pero desasociado de sus datos privados
    usuario_anon = db.query(Usuario).filter(Usuario.id == 1).first()
    assert usuario_anon.activo is False
    assert usuario_anon.nombre == "Usuario Anonimizado"
    assert "anon_1_" in usuario_anon.email
    db.close()


def test_10_creacion_productos_frontend_compatibilidad():
    """Valida la creación de productos usando campos estándar del frontend ('precio', cuotas, imagen, etc.)."""
    # Login admin
    res_login = client.post(
        "/auth/login",
        data={"username": "admin@tienda.com", "password": "AdminSecret123!"},
    )
    assert res_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # 1. Intento sin token -> 401
    res_sin_auth = client.post("/productos/", json={"nombre": "Sin Token", "precio": 1000})
    assert res_sin_auth.status_code == 401

    # 2. Creación con campos del frontend: 'precio', 'stock', 'garantia_meses', 'cuotas_cantidad', 'cuotas_valor'
    nuevo_producto = {
        "nombre": "Mancuerna Hexagonal Engomada 20kg",
        "descripcion": "Mancuerna ergonómica con recubrimiento de goma virgen",
        "precio": 65000.00,
        "stock": 15,
        "garantia_meses": 6,
        "cuotas_cantidad": 3,
        "cuotas_valor": 21666.67,
    }

    # Probar endpoint POST /productos/ (con trailing slash)
    res_post_slash = client.post("/productos/", json=nuevo_producto, headers=admin_headers)
    assert res_post_slash.status_code == 201, res_post_slash.text
    prod_data = res_post_slash.json()
    assert prod_data["id"] is not None
    assert prod_data["nombre"] == nuevo_producto["nombre"]
    assert float(prod_data["precio"]) == 65000.00
    assert float(prod_data["precio_final"]) == 65000.00
    assert prod_data["stock"] == 15
    assert prod_data["garantia_meses"] == 6
    assert prod_data["cuotas_cantidad"] == 3
    assert float(prod_data["cuotas_valor"]) == 21666.67

    # Probar endpoint POST /productos (sin trailing slash)
    nuevo_producto_2 = {
        "nombre": "Banco Regulable Multiajustable",
        "descripcion": "Estructura de acero reforzado",
        "precio_final": 120000.00,
        "stock": 5,
    }
    res_post_noslash = client.post("/productos", json=nuevo_producto_2, headers=admin_headers)
    assert res_post_noslash.status_code == 201, res_post_noslash.text
    prod_2_data = res_post_noslash.json()
    assert prod_2_data["id"] is not None
    assert prod_2_data["nombre"] == nuevo_producto_2["nombre"]

    # 3. Subir imagen vía POST /productos/{id}/imagen con campo "archivo" en FormData
    prod_id = prod_data["id"]
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    archivo_simulado = io.BytesIO(png_bytes)
    res_img = client.post(
        f"/productos/{prod_id}/imagen",
        files={"archivo": ("mancuerna20kg.png", archivo_simulado, "image/png")},
        headers=admin_headers,
    )
    assert res_img.status_code == 200, res_img.text
    data_con_img = res_img.json()
    assert data_con_img["id"] == prod_id
    assert data_con_img["imagen_url"] is not None
    assert f"/static/productos/{prod_id}-" in data_con_img["imagen_url"]

    # 4. Verificar que se persiste y devuelve en GET /productos/{id}
    res_get = client.get(f"/productos/{prod_id}")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["imagen_url"] == data_con_img["imagen_url"]
    assert float(data_get["precio_final"]) == 65000.00


def test_11_eliminacion_productos_y_categorias():
    """Valida eliminación segura con RBAC y filtrado por categoría temática."""
    # Login admin
    res_login = client.post(
        "/auth/login",
        data={"username": "admin@tienda.com", "password": "AdminSecret123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # Registrar y loguear cliente activo (dado que Juan se anonimizó en test_09)
    res_reg_c = client.post(
        "/auth/register",
        json={
            "nombre": "Cliente Nuevo",
            "email": "cliente_nuevo@ejemplo.com",
            "password": "Password123!",
            "acepto_tratamiento": True,
        },
    )
    assert res_reg_c.status_code == 201
    res_login_c = client.post(
        "/auth/login",
        data={"username": "cliente_nuevo@ejemplo.com", "password": "Password123!"},
    )
    assert res_login_c.status_code == 200
    cust_headers = {"Authorization": f"Bearer {res_login_c.json()['access_token']}"}

    # 1. Crear productos con categorías ("Gaming", "Anime")
    prod_gaming = client.post(
        "/productos/",
        json={"nombre": "Mouse Gamer RGB 16000 DPI", "precio": 35000, "stock": 10, "categoria": "Gaming"},
        headers=admin_headers,
    )
    assert prod_gaming.status_code == 201
    gaming_id = prod_gaming.json()["id"]

    prod_anime = client.post(
        "/productos/",
        json={"nombre": "Figura Coleccionable Anime 25cm", "precio": 52000, "stock": 4, "categoria": "Anime"},
        headers=admin_headers,
    )
    assert prod_anime.status_code == 201
    anime_id = prod_anime.json()["id"]

    # 2. Probar filtrado por categoría
    res_filter_gaming = client.get("/productos?categoria=Gaming")
    assert res_filter_gaming.status_code == 200
    items_gaming = res_filter_gaming.json()
    assert all(p["categoria"] == "Gaming" for p in items_gaming)
    assert any(p["id"] == gaming_id for p in items_gaming)

    res_filter_anime = client.get("/productos?categoria=Anime")
    assert res_filter_anime.status_code == 200
    items_anime = res_filter_anime.json()
    assert all(p["categoria"] == "Anime" for p in items_anime)

    # 3. Eliminar producto - Sin autenticación -> 401
    res_del_noauth = client.delete(f"/productos/{gaming_id}")
    assert res_del_noauth.status_code == 401

    # 4. Eliminar producto - Rol cliente -> 403
    res_del_cust = client.delete(f"/productos/{gaming_id}", headers=cust_headers)
    assert res_del_cust.status_code == 403

    # 5. Eliminar producto - ID inexistente -> 404
    res_del_404 = client.delete("/productos/999999", headers=admin_headers)
    assert res_del_404.status_code == 404

    # 6. Eliminar producto - Admin exitoso -> 200 OK con mensaje de éxito
    res_del_ok = client.delete(f"/productos/{gaming_id}", headers=admin_headers)
    assert res_del_ok.status_code == 200
    assert "Producto eliminado exitosamente" in res_del_ok.json()["mensaje"]

    # 7. Confirmar que ya no existe -> 404 en GET
    res_get_deleted = client.get(f"/productos/{gaming_id}")
    assert res_get_deleted.status_code == 404


def test_12_revocacion_plazo_legal_expirado():
    """Valida el límite perentorio de 10 días para el botón de arrepentimiento."""
    from datetime import datetime, timedelta, timezone
    from app.models.pedido import Pedido, ItemPedido

    # Crear un pedido con fecha de compra de 15 días atrás para el admin o crear un usuario activo
    db = TestingSessionLocal()
    admin_user = db.query(Usuario).filter(Usuario.email == "admin@tienda.com").first()
    fecha_antigua = datetime.now(timezone.utc) - timedelta(days=15)

    pedido_antiguo = Pedido(
        usuario_id=admin_user.id,
        estado="completado",
        total=50000.0,
        creado_en=fecha_antigua,
    )
    db.add(pedido_antiguo)
    db.commit()
    db.refresh(pedido_antiguo)
    pedido_id = pedido_antiguo.id
    db.close()

    # Login admin
    res_login = client.post(
        "/auth/login",
        data={"username": "admin@tienda.com", "password": "AdminSecret123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # Intentar revocar pedido de 15 días -> 400 Bad Request por plazo expirado (Ley 24.240)
    res_revoc_exp = client.post(f"/pedidos/{pedido_id}/revocacion", headers=admin_headers)
    assert res_revoc_exp.status_code == 400


def test_13_registro_con_admin_secret():
    """Valida la auto-asignación de is_admin = True mediante admin_secret."""
    # Registro con admin_secret válido
    res_admin = client.post(
        "/auth/register",
        json={
            "nombre": "Admin Nuevo",
            "email": "admin_nuevo@tienda.com",
            "password": "Password123!",
            "acepto_tratamiento": True,
            "admin_secret": "STICKER_ADMIN_2026",
        },
    )
    assert res_admin.status_code == 201
    data_admin = res_admin.json()
    assert data_admin["rol"] == "admin"
    assert data_admin["is_admin"] is True
    assert data_admin["es_admin"] is True

    # Registro con admin_secret inválido -> Se registra como customer común
    res_customer = client.post(
        "/auth/register",
        json={
            "nombre": "Cliente Comun",
            "email": "cliente_comun@tienda.com",
            "password": "Password123!",
            "acepto_tratamiento": True,
            "admin_secret": "CLAVE_INCORRECTA",
        },
    )
    assert res_customer.status_code == 201
    data_cust = res_customer.json()
    assert data_cust["rol"] == "customer"
    assert data_cust["is_admin"] is False


def test_14_script_create_admin():
    """Valida la función central del script create_admin.py y su persistencia segura."""
    from create_admin import crear_o_actualizar_admin
    from app.core.security import verificar_password

    # Crear admin mediante el script
    admin = crear_o_actualizar_admin(
        email="script_admin@tienda.com",
        nombre="Script Admin",
        password="ScriptPassword123!",
    )
    assert admin.id is not None
    assert admin.is_admin is True
    assert admin.es_admin is True
    assert admin.rol == "admin"
    assert verificar_password("ScriptPassword123!", admin.hashed_password)

    # Actualizar admin existente
    admin_upd = crear_o_actualizar_admin(
        email="script_admin@tienda.com",
        nombre="Script Admin Actualizado",
        password="NuevaPassword456!",
    )
    assert admin_upd.id == admin.id
    assert admin_upd.nombre == "Script Admin Actualizado"
    assert verificar_password("NuevaPassword456!", admin_upd.hashed_password)


def test_15_revocacion_por_admin_y_formato_respuesta():
    """Valida que un Administrador pueda revocar compras de terceros y la estructura de respuesta requerida."""
    # 1. Login cliente para crear un pedido
    res_login_cust = client.post(
        "/auth/login",
        data={"username": "cliente_comun@tienda.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login_cust.json()['access_token']}"}

    res_pedido = client.post(
        "/pedidos",
        headers=cust_headers,
        json={"items": [{"producto_id": 1, "cantidad": 1}]},
    )
    assert res_pedido.status_code == 201
    pedido_id = res_pedido.json()["id"]

    # 2. Login admin
    res_login_admin = client.post(
        "/auth/login",
        data={"username": "admin_nuevo@tienda.com", "password": "Password123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login_admin.json()['access_token']}"}

    # 3. El Admin ejecuta la revocación del pedido del cliente
    res_revoc = client.post(f"/pedidos/{pedido_id}/revocacion", headers=admin_headers)
    assert res_revoc.status_code == 201
    data_revoc = res_revoc.json()

    assert data_revoc["mensaje"] == "Solicitud de revocación procesada"
    assert data_revoc["estado"] == "cancelado"
    assert data_revoc["codigo_solicitud"].startswith("REV-2026-")

    # Confirmar en base de datos que el estado cambió a cancelado
    res_check = client.get(f"/pedidos/{pedido_id}", headers=admin_headers)
    assert res_check.json()["estado"] == "cancelado"


def test_16_historial_pedidos_admin_vs_cliente():
    """Valida que GET /pedidos y GET /pedidos/todos muestren todos los pedidos con comprador para Admin."""
    res_login_admin = client.post(
        "/auth/login",
        data={"username": "admin_nuevo@tienda.com", "password": "Password123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login_admin.json()['access_token']}"}

    res_login_cust = client.post(
        "/auth/login",
        data={"username": "cliente_comun@tienda.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login_cust.json()['access_token']}"}

    # Admin consulta /pedidos/
    res_admin_pedidos = client.get("/pedidos/", headers=admin_headers)
    assert res_admin_pedidos.status_code == 200
    pedidos_admin = res_admin_pedidos.json()
    assert len(pedidos_admin) >= 2  # Hay pedidos creados por distintos usuarios

    # Cada pedido para admin contiene datos del comprador
    primer_pedido = pedidos_admin[0]
    assert primer_pedido["comprador"] is not None
    assert "id" in primer_pedido["comprador"]
    assert "nombre" in primer_pedido["comprador"]
    assert "email" in primer_pedido["comprador"]

    # Consulta por alias /pedidos/todos
    res_admin_todos = client.get("/pedidos/todos", headers=admin_headers)
    assert res_admin_todos.status_code == 200
    assert len(res_admin_todos.json()) == len(pedidos_admin)

    # Cliente común consulta /pedidos/ -> solo sus pedidos
    res_cust_pedidos = client.get("/pedidos/", headers=cust_headers)
    assert res_cust_pedidos.status_code == 200
    for ped in res_cust_pedidos.json():
        assert ped["usuario_id"] == client.get("/auth/me", headers=cust_headers).json()["id"]


def test_17_cambio_estado_pedido_admin():
    """Valida PUT /pedidos/{id}/estado con require_admin y validación de estados."""
    res_login_admin = client.post(
        "/auth/login",
        data={"username": "admin_nuevo@tienda.com", "password": "Password123!"},
    )
    admin_headers = {"Authorization": f"Bearer {res_login_admin.json()['access_token']}"}

    res_login_cust = client.post(
        "/auth/login",
        data={"username": "cliente_comun@tienda.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {res_login_cust.json()['access_token']}"}

    # Crear un nuevo pedido
    res_pedido = client.post(
        "/pedidos",
        headers=cust_headers,
        json={"items": [{"producto_id": 1, "cantidad": 1}]},
    )
    pedido_id = res_pedido.json()["id"]

    # Cliente común intenta cambiar estado -> 403 Forbidden
    res_forb = client.put(
        f"/pedidos/{pedido_id}/estado",
        headers=cust_headers,
        json={"nuevo_estado": "aceptado"},
    )
    assert res_forb.status_code == 403

    # Admin intenta cambiar con estado inválido -> 422 Unprocessable Entity
    res_invalid = client.put(
        f"/pedidos/{pedido_id}/estado",
        headers=admin_headers,
        json={"nuevo_estado": "estado_magico"},
    )
    assert res_invalid.status_code == 422

    # Admin cambia a "aceptado" -> 200 OK
    res_ok = client.put(
        f"/pedidos/{pedido_id}/estado",
        headers=admin_headers,
        json={"nuevo_estado": "aceptado"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["estado"] == "aceptado"

    # Admin cambia a "enviado" -> 200 OK
    res_enviado = client.put(
        f"/pedidos/{pedido_id}/estado",
        headers=admin_headers,
        json={"nuevo_estado": "enviado"},
    )
    assert res_enviado.status_code == 200
    assert res_enviado.json()["estado"] == "enviado"
