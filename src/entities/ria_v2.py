from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from src.database.core import Base


class RiaV2GenerationLog(Base):
    __tablename__ = "ria_v2_generation_log"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    landing_page_id  = Column(PG_UUID(as_uuid=True), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False)
    seccion_lp_id    = Column(PG_UUID(as_uuid=True), ForeignKey("secciones_lp.id",  ondelete="CASCADE"), nullable=True)
    proyecto_id      = Column(PG_UUID(as_uuid=True), ForeignKey("proyectos.id",      ondelete="CASCADE"), nullable=False)
    user_id          = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),          nullable=False)
    cell_position    = Column(String(10),  nullable=False)
    block_type       = Column(String(50),  nullable=False)
    ai_generation_id = Column(PG_UUID(as_uuid=True), ForeignKey("ai_generations.id"), nullable=True)

    generation_number   = Column(Integer, nullable=False)
    clean_text          = Column(Text, nullable=False)
    word_count          = Column(Integer, nullable=False)
    was_ultimately_used = Column(Boolean, default=None, nullable=True)

    model_version = Column(String(20), nullable=False, default="RIA-V2")
    created_at    = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        Index("idx_ria_gen_lp_cell",  "landing_page_id", "cell_position"),
        Index("idx_ria_gen_lp_block", "landing_page_id", "block_type"),
        Index("idx_ria_gen_seccion",  "seccion_lp_id"),
        Index("idx_ria_gen_user",     "user_id", "created_at"),
    )


class RiaV2SaveLog(Base):
    __tablename__ = "ria_v2_save_log"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    landing_page_id = Column(PG_UUID(as_uuid=True), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False)
    seccion_lp_id   = Column(PG_UUID(as_uuid=True), ForeignKey("secciones_lp.id",  ondelete="CASCADE"), nullable=True)
    proyecto_id     = Column(PG_UUID(as_uuid=True), ForeignKey("proyectos.id",      ondelete="CASCADE"), nullable=False)
    user_id         = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),          nullable=False)
    cell_position   = Column(String(10), nullable=True)   # NULL: log es por bloque, no por celda
    block_type      = Column(String(50), nullable=False)

    clean_text_saved  = Column(Text, nullable=False)
    word_count_saved  = Column(Integer, nullable=False)

    last_generation_id          = Column(PG_UUID(as_uuid=True), ForeignKey("ria_v2_generation_log.id"), nullable=True)
    generation_number_used      = Column(Integer, nullable=True)
    total_generations_for_block = Column(Integer, nullable=False, default=0)

    words_from_ai    = Column(Integer, nullable=True)
    words_added      = Column(Integer, nullable=True)
    words_removed    = Column(Integer, nullable=True)
    pct_ai_kept      = Column(Float,   nullable=True)
    acceptance_level = Column(String(20), nullable=True)

    save_number   = Column(Integer, nullable=False, default=1)
    model_version = Column(String(20), nullable=False, default="RIA-V2")
    created_at    = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        Index("idx_ria_save_lp_block",    "landing_page_id", "block_type"),
        Index("idx_ria_save_seccion",      "seccion_lp_id"),
        Index("idx_ria_save_acceptance",   "acceptance_level"),
        Index("idx_ria_save_user",         "user_id", "created_at"),
    )


class RiaV2BlockSession(Base):
    __tablename__ = "ria_v2_block_session"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    landing_page_id = Column(PG_UUID(as_uuid=True), ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False)
    seccion_lp_id   = Column(PG_UUID(as_uuid=True), ForeignKey("secciones_lp.id",  ondelete="CASCADE"), nullable=True)
    proyecto_id     = Column(PG_UUID(as_uuid=True), ForeignKey("proyectos.id",      ondelete="CASCADE"), nullable=False)
    user_id         = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),          nullable=False)
    cell_position   = Column(String(10), nullable=True)   # NULL: sesión es por bloque
    block_type      = Column(String(50), nullable=False)

    total_generation_attempts = Column(Integer, nullable=False, default=0)
    generation_used_number    = Column(Integer, nullable=True)
    total_saves               = Column(Integer, nullable=False, default=0)

    first_generation_at = Column(String, nullable=True)
    last_saved_at       = Column(String, nullable=True)

    final_pct_ai_kept      = Column(Float,    nullable=True)
    final_acceptance_level = Column(String(20), nullable=True)
    acceptance_evolution   = Column(JSONB, nullable=False, default=list)
    went_to_manual         = Column(Boolean, nullable=False, default=False)

    model_version = Column(String(20), nullable=False, default="RIA-V2")
    created_at    = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at    = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        UniqueConstraint("landing_page_id", "block_type", name="uq_ria_session_lp_block"),
        Index("idx_ria_session_lp",        "landing_page_id"),
        Index("idx_ria_session_user",       "user_id"),
        Index("idx_ria_session_acceptance", "final_acceptance_level"),
        Index("idx_ria_session_block_type", "block_type", "final_acceptance_level"),
    )
