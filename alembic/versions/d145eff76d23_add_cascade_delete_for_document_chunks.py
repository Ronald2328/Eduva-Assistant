"""add cascade delete for document chunks

Revision ID: d145eff76d23
Revises: 4e7c40378a1a
Create Date: 2026-04-04 19:04:52.929606

"""
from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd145eff76d23'
down_revision: str | Sequence[str] | None = '4e7c40378a1a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "document_chunks"
_REFERRED_TABLE = "documents"
_COLUMN = "document_id"
_FK_NAME = "fk_document_chunks_document_id_documents"


def _drop_document_chunks_fk() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = inspector.get_foreign_keys(_TABLE)

    target_fk_name: str | None = None
    for fk in fks:
        constrained_cols = fk.get("constrained_columns", [])
        referred_table = fk.get("referred_table")
        if constrained_cols == [_COLUMN] and referred_table == _REFERRED_TABLE:
            target_fk_name = fk.get("name")
            break

    if target_fk_name:
        op.drop_constraint(target_fk_name, _TABLE, type_="foreignkey")


def upgrade() -> None:
    """Upgrade schema."""
    _drop_document_chunks_fk()
    op.create_foreign_key(
        _FK_NAME,
        _TABLE,
        _REFERRED_TABLE,
        [_COLUMN],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    _drop_document_chunks_fk()
    op.create_foreign_key(
        _FK_NAME,
        _TABLE,
        _REFERRED_TABLE,
        [_COLUMN],
        ["id"],
    )
