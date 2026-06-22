"""Collect engagement and body metrics

Revision ID: 003_collect_engagement_metrics
Revises: 002_add_reason_feedback
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_collect_engagement_metrics'
down_revision: Union[str, None] = '002_add_reason_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('height_cm', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('weight_kg', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('body_shape', sa.String(length=64), nullable=True))

    op.add_column('garments', sa.Column('tryon_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('garments', sa.Column('favorite_count', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('feedbacks', sa.Column('garment_id', sa.Integer(), nullable=True))
    op.add_column('feedbacks', sa.Column('tryon_record_id', sa.Integer(), nullable=True))
    op.add_column('feedbacks', sa.Column('fit_status', sa.String(length=64), nullable=True))

    op.create_foreign_key('fk_feedbacks_garment_id_garments', 'feedbacks', 'garments', ['garment_id'], ['id'])
    op.create_foreign_key('fk_feedbacks_tryon_record_id_tryon_records', 'feedbacks', 'tryon_records', ['tryon_record_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_feedbacks_tryon_record_id_tryon_records', 'feedbacks', type_='foreignkey')
    op.drop_constraint('fk_feedbacks_garment_id_garments', 'feedbacks', type_='foreignkey')

    op.drop_column('feedbacks', 'fit_status')
    op.drop_column('feedbacks', 'tryon_record_id')
    op.drop_column('feedbacks', 'garment_id')

    op.drop_column('garments', 'favorite_count')
    op.drop_column('garments', 'tryon_count')

    op.drop_column('users', 'body_shape')
    op.drop_column('users', 'weight_kg')
    op.drop_column('users', 'height_cm')
