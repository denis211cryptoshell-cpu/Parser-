"""Initial tables - monitored_chats, keywords, parsed_messages

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: None


def upgrade() -> None:
    op.create_table('keywords',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('word', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word')
    )
    op.create_index(op.f('ix_keywords_word'), 'keywords', ['word'], unique=True)
    
    op.create_table('monitored_chats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_title', sa.String(length=255), nullable=True),
        sa.Column('chat_username', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id'),
        sa.UniqueConstraint('chat_username')
    )
    op.create_index(op.f('ix_monitored_chats_chat_id'), 'monitored_chats', ['chat_id'], unique=True)
    
    op.create_table('parsed_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_title', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('matched_keywords', sa.String(length=500), nullable=True),
        sa.Column('message_link', sa.String(length=500), nullable=True),
        sa.Column('parsed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parsed_messages_message_id'), 'parsed_messages', ['message_id'], unique=False)
    op.create_index(op.f('ix_parsed_messages_chat_id'), 'parsed_messages', ['chat_id'], unique=False)
    op.create_index(op.f('ix_parsed_messages_user_id'), 'parsed_messages', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_parsed_messages_user_id'), table_name='parsed_messages')
    op.drop_index(op.f('ix_parsed_messages_chat_id'), table_name='parsed_messages')
    op.drop_index(op.f('ix_parsed_messages_message_id'), table_name='parsed_messages')
    op.drop_table('parsed_messages')
    op.drop_index(op.f('ix_monitored_chats_chat_id'), table_name='monitored_chats')
    op.drop_table('monitored_chats')
    op.drop_index(op.f('ix_keywords_word'), table_name='keywords')
    op.drop_table('keywords')
