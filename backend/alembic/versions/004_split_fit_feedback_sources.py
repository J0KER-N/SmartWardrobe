"""Split fit feedback sources and size bindings

Revision ID: 004_split_fit_feedback_sources
Revises: 003_collect_engagement_metrics
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_split_fit_feedback_sources"
down_revision: Union[str, None] = "003_collect_engagement_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedbacks", sa.Column("fit_source", sa.String(length=32), nullable=False, server_default="online"))
    op.add_column("feedbacks", sa.Column("garment_size", sa.String(length=64), nullable=True))
    op.add_column("feedbacks", sa.Column("body_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("feedbacks", "body_snapshot")
    op.drop_column("feedbacks", "garment_size")
    op.drop_column("feedbacks", "fit_source")
