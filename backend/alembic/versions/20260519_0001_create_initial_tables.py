"""create initial tables

Revision ID: 20260519_0001
Revises:
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260519_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_id", "files", ["id"], unique=False)
    op.create_index("ix_files_filename", "files", ["filename"], unique=True)

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", "chunk_index", name="uq_file_chunk_index"),
    )
    op.create_index("ix_chunks_id", "chunks", ["id"], unique=False)
    op.create_index("ix_chunks_file_chunk", "chunks", ["file_id", "chunk_index"], unique=False)

    op.create_table(
        "chunk_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=64), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "node_name", name="uq_chunk_node"),
    )
    op.create_index("ix_chunk_locations_id", "chunk_locations", ["id"], unique=False)
    op.create_index("ix_chunk_locations_chunk_node", "chunk_locations", ["chunk_id", "node_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chunk_locations_chunk_node", table_name="chunk_locations")
    op.drop_index("ix_chunk_locations_id", table_name="chunk_locations")
    op.drop_table("chunk_locations")
    op.drop_index("ix_chunks_file_chunk", table_name="chunks")
    op.drop_index("ix_chunks_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_files_filename", table_name="files")
    op.drop_index("ix_files_id", table_name="files")
    op.drop_table("files")
