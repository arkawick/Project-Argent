"""Initial schema — all five tables

Revision ID: 0001
Revises:
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── customers ──────────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("tier", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("lifetime_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("first_contact", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_contact", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", JSONB, nullable=False, server_default="{}"),
        sa.Column("tags", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_customers_phone", "customers", ["phone"])
    op.create_index("idx_customers_email", "customers", ["email"])
    op.create_index("idx_customers_tier", "customers", ["tier"])

    # ── calls ──────────────────────────────────────────────────────────────────
    op.create_table(
        "calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("livekit_room_id", sa.String(255), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_secs", sa.Integer, nullable=True),
        sa.Column("agent_type", sa.String(30), nullable=True),
        sa.Column("transcript", JSONB, nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("sentiment_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("recording_url", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_calls_customer_id", "calls", ["customer_id"])
    op.create_index("idx_calls_status", "calls", ["status"])
    op.create_index("idx_calls_started_at", "calls", ["started_at"])
    op.create_index("idx_calls_agent_type", "calls", ["agent_type"])

    # ── appointments ───────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_mins", sa.Integer, nullable=False, server_default="30"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("agent_notes", sa.Text, nullable=True),
        sa.Column("reminder_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_appointments_customer_id", "appointments", ["customer_id"])
    op.create_index("idx_appointments_scheduled_at", "appointments", ["scheduled_at"])
    op.create_index("idx_appointments_status", "appointments", ["status"])

    # ── call_insights ──────────────────────────────────────────────────────────
    op.create_table(
        "call_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_number", sa.Integer, nullable=False),
        sa.Column("speaker", sa.String(10), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("timestamp_secs", sa.Numeric(8, 3), nullable=True),
        sa.Column("emotion", sa.String(30), nullable=True),
        sa.Column("emotion_conf", sa.Numeric(4, 3), nullable=True),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("intent_conf", sa.Numeric(4, 3), nullable=True),
        sa.Column("barge_in", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_insights_call_id", "call_insights", ["call_id"])
    op.create_index("idx_insights_emotion", "call_insights", ["emotion"])
    op.create_index("idx_insights_intent", "call_insights", ["intent"])
    op.create_index("idx_insights_speaker", "call_insights", ["speaker"])

    # ── tickets ────────────────────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tickets_customer_id", "tickets", ["customer_id"])
    op.create_index("idx_tickets_status", "tickets", ["status"])
    op.create_index("idx_tickets_priority", "tickets", ["priority"])


def downgrade() -> None:
    op.drop_table("tickets")
    op.drop_table("call_insights")
    op.drop_table("appointments")
    op.drop_table("calls")
    op.drop_table("customers")
