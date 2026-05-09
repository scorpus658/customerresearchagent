import enum
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    interviews = relationship("Interview", back_populates="project")
    board = relationship("ProjectBoard", back_populates="project", uselist=False, cascade="all, delete-orphan")


class InterviewStatus(str, enum.Enum):
    uploaded = "uploaded"
    transcribing = "transcribing"
    analyzing = "analyzing"
    synthesizing = "synthesizing"
    complete = "complete"
    error = "error"


class FileType(str, enum.Enum):
    transcript = "transcript"
    audio = "audio"
    video = "video"


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(512), nullable=False)
    status = Column(
        Enum(InterviewStatus, name="interview_status"),
        nullable=False,
        default=InterviewStatus.uploaded,
        index=True,
    )
    original_filename = Column(String(1024), nullable=False)
    file_type = Column(Enum(FileType, name="file_type"), nullable=False)
    file_url = Column(String(2048), nullable=True)
    language_detected = Column(String(32), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    project = relationship("Project", back_populates="interviews")
    profile = relationship(
        "IntervieweeProfile", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
    transcript = relationship(
        "Transcript", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
    analysis = relationship(
        "Analysis", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
    report = relationship(
        "Report", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_text = Column(Text, nullable=True)
    segments = Column(JSON, nullable=True)  # [{speaker, text, start_time, end_time, language, translated_text}]
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    interview = relationship("Interview", back_populates="transcript")

    __table_args__ = (
        Index("ix_transcripts_interview_id", "interview_id"),
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    pain_points = Column(JSON, nullable=True)
    goals = Column(JSON, nullable=True)
    objections = Column(JSON, nullable=True)
    feature_requests = Column(JSON, nullable=True)
    workarounds = Column(JSON, nullable=True)
    emotional_moments = Column(JSON, nullable=True)
    strong_quotes = Column(JSON, nullable=True)
    raw_extraction = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    interview = relationship("Interview", back_populates="analysis")

    __table_args__ = (
        Index("ix_analyses_interview_id", "interview_id"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    executive_summary = Column(Text, nullable=True)
    detailed_findings = Column(JSON, nullable=True)
    themes = Column(JSON, nullable=True)  # [{name, description, insights, evidence_count}]
    recommendations = Column(JSON, nullable=True)
    report_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    interview = relationship("Interview", back_populates="report")

    __table_args__ = (
        Index("ix_reports_interview_id", "interview_id"),
    )


class BoardStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    error = "error"


class IntervieweeProfile(Base):
    """Structured demographic/context profile for one interview's participant."""
    __tablename__ = "interviewee_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Extracted fields (None = not found in transcript)
    name = Column(String(256), nullable=True)
    age_range = Column(String(32), nullable=True)       # e.g. "26-35"
    role = Column(String(256), nullable=True)
    company_size = Column(String(64), nullable=True)    # e.g. "startup(<10)"
    industry = Column(String(256), nullable=True)
    tech_level = Column(String(64), nullable=True)      # "non-technical" … "very-technical"
    financial_context = Column(Text, nullable=True)     # direct quotes about budget/spend
    location = Column(String(256), nullable=True)
    notes = Column(Text, nullable=True)
    # Which fields the extractor couldn't determine from the transcript
    missing_fields = Column(JSON, nullable=True)        # list[str]
    # Whether the user has already been prompted for missing fields
    user_filled = Column(String(8), nullable=False, default="no")  # "no" | "partial" | "done"
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    interview = relationship("Interview", back_populates="profile")

    __table_args__ = (
        Index("ix_interviewee_profiles_interview_id", "interview_id"),
    )


class ProjectBoard(Base):
    """Cross-interview research board for a project."""
    __tablename__ = "project_boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status = Column(
        Enum(BoardStatus, name="board_status"),
        nullable=False,
        default=BoardStatus.pending,
    )
    error_message = Column(Text, nullable=True)
    # Synthesis outputs
    recurring_themes = Column(JSON, nullable=True)      # [{name, count, interviews, description}]
    pain_points = Column(JSON, nullable=True)           # [{text, count, interviews, quotes}]
    unique_insights = Column(JSON, nullable=True)       # [{text, interview, quote}]
    patterns = Column(JSON, nullable=True)              # [{title, description, evidence}]
    demographic_summary = Column(JSON, nullable=True)   # {age_ranges, roles, industries, …}
    data_gaps = Column(JSON, nullable=True)             # [{question, missing_in_n_interviews}]
    interviews_included = Column(JSON, nullable=True)   # list of interview ids synthesized
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    project = relationship("Project", back_populates="board")

    __table_args__ = (
        Index("ix_project_boards_project_id", "project_id"),
    )


async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
