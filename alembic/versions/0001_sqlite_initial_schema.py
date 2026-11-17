"""Migracion inicial para SQLite

Revision ID: 0001_sqlite_initial
Revises:
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_sqlite_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea el esquema completo de tablas compatible con SQLite."""
    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.String(length=1000), nullable=True),
        sa.Column("precio_final", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cuotas_cantidad", sa.Integer(), nullable=False),
        sa.Column("cuotas_valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("garantia_meses", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("imagen_url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_productos_id"), "productos", ["id"], unique=False)
    op.create_index(op.f("ix_productos_nombre"), "productos", ["nombre"], unique=False)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=50), nullable=False),
        sa.Column("acepto_tratamiento", sa.Boolean(), nullable=False),
        sa.Column("fecha_consentimiento", sa.DateTime(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("fecha_baja", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)

    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=50), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pedidos_id"), "pedidos", ["id"], unique=False)

    op.create_table(
        "items_pedido",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_pedido_id"), "items_pedido", ["id"], unique=False)

    op.create_table(
        "solicitudes_revocacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=100), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pedido_id"),
    )
    op.create_index(
        op.f("ix_solicitudes_revocacion_codigo"),
        "solicitudes_revocacion",
        ["codigo"],
        unique=True,
    )
    op.create_index(
        op.f("ix_solicitudes_revocacion_id"),
        "solicitudes_revocacion",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Elimina todas las tablas del esquema."""
    op.drop_index(op.f("ix_solicitudes_revocacion_id"), table_name="solicitudes_revocacion")
    op.drop_index(op.f("ix_solicitudes_revocacion_codigo"), table_name="solicitudes_revocacion")
    op.drop_table("solicitudes_revocacion")
    op.drop_index(op.f("ix_items_pedido_id"), table_name="items_pedido")
    op.drop_table("items_pedido")
    op.drop_index(op.f("ix_pedidos_id"), table_name="pedidos")
    op.drop_table("pedidos")
    op.drop_index(op.f("ix_usuarios_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_email"), table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_index(op.f("ix_productos_nombre"), table_name="productos")
    op.drop_index(op.f("ix_productos_id"), table_name="productos")
    op.drop_table("productos")
