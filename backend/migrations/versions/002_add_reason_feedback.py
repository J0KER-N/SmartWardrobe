"""Add reason field and feedback table

Revision ID: 002_add_reason_feedback
Revises: 
Create Date: 2026-05-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_reason_feedback'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 在 garments 表中添加 reason 字段（标签识别理由）
    op.add_column('garments', sa.Column('reason', sa.String(length=500), nullable=True))
    
    # 2. 创建 feedbacks 表（用户反馈）
    op.create_table('feedbacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('garment_id', sa.Integer(), nullable=True),
        sa.Column('tryon_record_id', sa.Integer(), nullable=True),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('feedback_text', sa.String(length=1000), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['garment_id'], ['garments.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tryon_record_id'], ['try_on_records.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # 为 feedbacks 表创建索引
    op.create_index(op.f('ix_feedbacks_id'), 'feedbacks', ['id'], unique=False)
    op.create_index(op.f('ix_feedbacks_owner_id'), 'feedbacks', ['owner_id'], unique=False)
    op.create_index(op.f('ix_feedbacks_garment_id'), 'feedbacks', ['garment_id'], unique=False)
    op.create_index(op.f('ix_feedbacks_tryon_record_id'), 'feedbacks', ['tryon_record_id'], unique=False)


def downgrade() -> None:
    # 回滚：删除 feedbacks 表和索引
    op.drop_index(op.f('ix_feedbacks_tryon_record_id'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_garment_id'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_owner_id'), table_name='feedbacks')
    op.drop_index(op.f('ix_feedbacks_id'), table_name='feedbacks')
    op.drop_table('feedbacks')
    
    # 回滚：删除 garments 表中的 reason 字段
    op.drop_column('garments', 'reason')
