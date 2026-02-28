"""Initial migration with documents and pages tables

Revision ID: b4902152be8b
Revises:
Create Date: 2026-02-28 11:50:44.312089

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4902152be8b'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(length=500), nullable=False),
        sa.Column("tipo", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes on documents table
    op.create_index("idx_documents_tipo", "documents", ["tipo"], unique=False)

    # Create pages table
    op.execute("""
        CREATE TABLE pages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre_archivo VARCHAR(500) NOT NULL,
            pagina INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Create indexes on pages table
    op.create_index("idx_pages_nombre_archivo", "pages", ["nombre_archivo"], unique=False)
    op.create_index("idx_pages_pagina", "pages", ["pagina"], unique=False)

    # Create HNSW index for vector search
    op.execute("""
        CREATE INDEX idx_pages_embedding_hnsw ON pages
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_pages_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_pages_pagina")
    op.execute("DROP INDEX IF EXISTS idx_pages_nombre_archivo")
    op.execute("DROP TABLE IF EXISTS pages")

    op.drop_index("idx_documents_tipo", table_name="documents")
    op.drop_table("documents")

    op.execute("DROP EXTENSION IF EXISTS vector")
