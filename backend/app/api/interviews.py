"""Interview API endpoints."""

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.database import (
    Analysis,
    FileType,
    Interview,
    InterviewStatus,
    IntervieweeProfile,
    Report,
    Transcript,
    get_session,
)
from app.services.pdf_generator import generate_report_pdf
from app.services.storage import StorageService
from app.workers.pipeline import get_arq_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

TRANSCRIPT_EXTENSIONS = {".txt", ".json", ".srt", ".vtt"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
ALLOWED_EXTENSIONS = TRANSCRIPT_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

storage = StorageService()


# ---------- Pydantic schemas ----------

class InterviewOut(BaseModel):
    id: str
    project_id: str | None = None
    title: str
    status: str
    original_filename: str
    file_type: str
    file_url: str | None = None
    language_detected: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class TranscriptOut(BaseModel):
    id: str
    interview_id: str
    raw_text: str | None = None
    segments: list[dict[str, Any]] | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AnalysisOut(BaseModel):
    id: str
    interview_id: str
    pain_points: list[dict[str, Any]] | None = None
    goals: list[dict[str, Any]] | None = None
    objections: list[dict[str, Any]] | None = None
    feature_requests: list[dict[str, Any]] | None = None
    workarounds: list[dict[str, Any]] | None = None
    emotional_moments: list[dict[str, Any]] | None = None
    strong_quotes: list[dict[str, Any]] | None = None
    raw_extraction: list[dict[str, Any]] | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    interview_id: str
    executive_summary: str | None = None
    detailed_findings: dict[str, Any] | None = None
    themes: list[dict[str, Any]] | None = None
    recommendations: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ReportUpdateIn(BaseModel):
    executive_summary: str | None = None
    detailed_findings: dict[str, Any] | None = None
    themes: list[dict[str, Any]] | None = None
    recommendations: list[dict[str, Any]] | None = None


class InterviewDetailOut(BaseModel):
    interview: InterviewOut
    transcript: TranscriptOut | None = None
    analysis: AnalysisOut | None = None
    report: ReportOut | None = None


class PaginatedInterviews(BaseModel):
    items: list[InterviewOut]
    total: int
    limit: int
    offset: int


# ---------- Helpers ----------

def _serialize_interview(interview: Interview) -> InterviewOut:
    return InterviewOut(
        id=str(interview.id),
        project_id=str(interview.project_id) if interview.project_id else None,
        title=interview.title,
        status=interview.status.value,
        original_filename=interview.original_filename,
        file_type=interview.file_type.value,
        file_url=interview.file_url,
        language_detected=interview.language_detected,
        error_message=interview.error_message,
        created_at=interview.created_at.isoformat(),
        updated_at=interview.updated_at.isoformat(),
    )


def _serialize_transcript(t: Transcript) -> TranscriptOut:
    return TranscriptOut(
        id=str(t.id),
        interview_id=str(t.interview_id),
        raw_text=t.raw_text,
        segments=t.segments,
        created_at=t.created_at.isoformat(),
    )


def _serialize_analysis(a: Analysis) -> AnalysisOut:
    return AnalysisOut(
        id=str(a.id),
        interview_id=str(a.interview_id),
        pain_points=a.pain_points,
        goals=a.goals,
        objections=a.objections,
        feature_requests=a.feature_requests,
        workarounds=a.workarounds,
        emotional_moments=a.emotional_moments,
        strong_quotes=a.strong_quotes,
        raw_extraction=a.raw_extraction,
        created_at=a.created_at.isoformat(),
    )


def _serialize_report(r: Report) -> ReportOut:
    return ReportOut(
        id=str(r.id),
        interview_id=str(r.interview_id),
        executive_summary=r.executive_summary,
        detailed_findings=r.detailed_findings,
        themes=r.themes,
        recommendations=r.recommendations,
        metadata=r.report_metadata,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


def _determine_file_type(ext: str) -> FileType:
    if ext in TRANSCRIPT_EXTENSIONS:
        return FileType.transcript
    elif ext in AUDIO_EXTENSIONS:
        return FileType.audio
    elif ext in VIDEO_EXTENSIONS:
        return FileType.video
    raise ValueError(f"Unsupported file extension: {ext}")


# ---------- Endpoints ----------

@router.post("/upload", response_model=InterviewOut, status_code=201)
async def upload_interview(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    project_id: str | None = Form(default=None),
    participant_name: str | None = Form(default=None),
    participant_age_range: str | None = Form(default=None),
    participant_role: str | None = Form(default=None),
    synthesis_model: str = Form(default='haiku'),
    session: AsyncSession = Depends(get_session),
) -> InterviewOut:
    """Upload a transcript, audio, or video file for analysis."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and validate file size
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    # Generate unique filename
    file_id = uuid.uuid4()
    safe_filename = f"{file_id}{ext}"
    title = (title.strip() if title else None) or Path(file.filename).stem

    # Save locally
    local_path = await storage.save_file(content, safe_filename)

    # Optionally upload to S3
    s3_url = await storage.upload_to_s3(local_path, f"interviews/{safe_filename}")

    file_type = _determine_file_type(ext)

    # Determine initial status
    if file_type == FileType.transcript:
        initial_status = InterviewStatus.analyzing
    else:
        initial_status = InterviewStatus.transcribing

    parsed_project_id: uuid.UUID | None = None
    if project_id:
        try:
            parsed_project_id = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id")

    interview = Interview(
        project_id=parsed_project_id,
        title=title,
        status=initial_status,
        original_filename=file.filename,
        file_type=file_type,
        file_url=local_path,
    )
    session.add(interview)
    await session.flush()
    await session.refresh(interview)

    # Pre-save participant profile if any fields were provided at upload time
    if any([participant_name, participant_age_range, participant_role]):
        from app.services.profile_extractor import PROFILE_FIELDS
        prefilled = {
            "name": participant_name.strip() if participant_name else None,
            "age_range": participant_age_range.strip() if participant_age_range else None,
            "role": participant_role.strip() if participant_role else None,
        }
        missing = [f for f in PROFILE_FIELDS if not prefilled.get(f)]
        session.add(IntervieweeProfile(
            interview_id=interview.id,
            name=prefilled["name"],
            age_range=prefilled["age_range"],
            role=prefilled["role"],
            missing_fields=missing,
            user_filled="partial" if missing else "done",
        ))
        await session.flush()

    # Queue background processing
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job("process_interview", str(interview.id), synthesis_model)
        logger.info("Enqueued processing job for interview %s", interview.id)
    except Exception as exc:
        logger.error("Failed to enqueue job for interview %s: %s", interview.id, exc)
        interview.status = InterviewStatus.error
        interview.error_message = f"Failed to queue processing: {exc}"

    return _serialize_interview(interview)


@router.get("", response_model=PaginatedInterviews)
async def list_interviews(
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> PaginatedInterviews:
    """List interviews with optional project filter."""
    filter_clause = []
    if project_id:
        try:
            pid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project_id")
        filter_clause.append(Interview.project_id == pid)

    count_q = select(func.count()).select_from(Interview)
    if filter_clause:
        count_q = count_q.where(*filter_clause)
    total_result = await session.execute(count_q)
    total = total_result.scalar_one()

    q = select(Interview).order_by(Interview.created_at.desc()).limit(limit).offset(offset)
    if filter_clause:
        q = q.where(*filter_clause)
    result = await session.execute(q)
    interviews = result.scalars().all()

    return PaginatedInterviews(
        items=[_serialize_interview(i) for i in interviews],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[InterviewOut])
async def search_interviews(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_session),
) -> list[InterviewOut]:
    """Full-text search across transcripts, reports, and interview titles."""
    pattern = f"%{q}%"

    # Search interviews by title
    interview_ids_q = select(Interview.id).where(Interview.title.ilike(pattern))

    # Search transcripts by raw_text
    transcript_ids_q = select(Transcript.interview_id).where(
        Transcript.raw_text.ilike(pattern)
    )

    # Search reports by executive_summary
    report_ids_q = select(Report.interview_id).where(
        Report.executive_summary.ilike(pattern)
    )

    combined = select(Interview).where(
        or_(
            Interview.id.in_(interview_ids_q),
            Interview.id.in_(transcript_ids_q),
            Interview.id.in_(report_ids_q),
        )
    ).order_by(Interview.created_at.desc()).limit(50)

    result = await session.execute(combined)
    interviews = result.scalars().all()
    return [_serialize_interview(i) for i in interviews]


@router.get("/{interview_id}", response_model=InterviewDetailOut)
async def get_interview(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> InterviewDetailOut:
    """Get full interview detail with transcript, analysis, and report."""
    q = (
        select(Interview)
        .options(
            selectinload(Interview.transcript),
            selectinload(Interview.analysis),
            selectinload(Interview.report),
        )
        .where(Interview.id == interview_id)
    )
    result = await session.execute(q)
    interview = result.scalar_one_or_none()

    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    return InterviewDetailOut(
        interview=_serialize_interview(interview),
        transcript=_serialize_transcript(interview.transcript) if interview.transcript else None,
        analysis=_serialize_analysis(interview.analysis) if interview.analysis else None,
        report=_serialize_report(interview.report) if interview.report else None,
    )


@router.get("/{interview_id}/transcript", response_model=TranscriptOut)
async def get_transcript(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptOut:
    """Get just the transcript for an interview."""
    q = select(Transcript).where(Transcript.interview_id == interview_id)
    result = await session.execute(q)
    transcript = result.scalar_one_or_none()
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return _serialize_transcript(transcript)


@router.get("/{interview_id}/analysis", response_model=AnalysisOut)
async def get_analysis(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AnalysisOut:
    """Get just the analysis for an interview."""
    q = select(Analysis).where(Analysis.interview_id == interview_id)
    result = await session.execute(q)
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _serialize_analysis(analysis)


@router.get("/{interview_id}/report", response_model=ReportOut)
async def get_report(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ReportOut:
    """Get just the report for an interview."""
    q = select(Report).where(Report.interview_id == interview_id)
    result = await session.execute(q)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(report)


@router.patch("/{interview_id}/report", response_model=ReportOut)
async def update_report(
    interview_id: uuid.UUID,
    body: ReportUpdateIn,
    session: AsyncSession = Depends(get_session),
) -> ReportOut:
    """Edit report fields."""
    q = select(Report).where(Report.interview_id == interview_id)
    result = await session.execute(q)
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)

    await session.flush()
    await session.refresh(report)
    return _serialize_report(report)


@router.get("/{interview_id}/export")
async def export_report(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Export the full report as a PDF."""
    q = (
        select(Interview)
        .options(
            selectinload(Interview.transcript),
            selectinload(Interview.analysis),
            selectinload(Interview.report),
        )
        .where(Interview.id == interview_id)
    )
    result = await session.execute(q)
    interview = result.scalar_one_or_none()

    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    interview_dict = {
        "id": str(interview.id),
        "title": interview.title,
        "original_filename": interview.original_filename,
        "language_detected": interview.language_detected,
        "created_at": interview.created_at.isoformat(),
    }

    transcript_dict = None
    if interview.transcript:
        transcript_dict = {
            "raw_text": interview.transcript.raw_text,
            "segments": interview.transcript.segments or [],
        }

    analysis_dict = None
    if interview.analysis:
        analysis_dict = {
            "pain_points": interview.analysis.pain_points or [],
            "goals": interview.analysis.goals or [],
            "objections": interview.analysis.objections or [],
            "feature_requests": interview.analysis.feature_requests or [],
            "workarounds": interview.analysis.workarounds or [],
            "emotional_moments": interview.analysis.emotional_moments or [],
            "strong_quotes": interview.analysis.strong_quotes or [],
        }

    report_dict = None
    if interview.report:
        report_dict = {
            "executive_summary": interview.report.executive_summary,
            "detailed_findings": interview.report.detailed_findings,
            "themes": interview.report.themes or [],
            "recommendations": interview.report.recommendations or [],
        }

    pdf_bytes = generate_report_pdf(interview_dict, transcript_dict, analysis_dict, report_dict)
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in interview.title)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}_report.pdf"'},
    )


@router.delete("/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an interview and all associated data."""
    q = select(Interview).where(Interview.id == interview_id)
    result = await session.execute(q)
    interview = result.scalar_one_or_none()

    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Delete local file
    if interview.file_url:
        await storage.delete_file(interview.file_url)

    await session.delete(interview)


class ReprocessBody(BaseModel):
    synthesis_model: str = "haiku"


@router.post("/{interview_id}/reprocess", response_model=InterviewOut)
async def reprocess_interview(
    interview_id: uuid.UUID,
    body: ReprocessBody = ReprocessBody(),
    session: AsyncSession = Depends(get_session),
) -> InterviewOut:
    """Rerun the analysis pipeline for an interview."""
    q = select(Interview).where(Interview.id == interview_id)
    result = await session.execute(q)
    interview = result.scalar_one_or_none()

    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Clear existing analysis and report
    await session.execute(
        delete(Analysis).where(Analysis.interview_id == interview_id)
    )
    await session.execute(
        delete(Report).where(Report.interview_id == interview_id)
    )

    # Reset status
    if interview.file_type == FileType.transcript:
        interview.status = InterviewStatus.analyzing
    else:
        # Also re-delete transcript for audio/video to re-transcribe
        await session.execute(
            delete(Transcript).where(Transcript.interview_id == interview_id)
        )
        interview.status = InterviewStatus.transcribing

    interview.error_message = None
    await session.flush()
    await session.refresh(interview)

    # Re-queue
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job("process_interview", str(interview.id), body.synthesis_model)
        logger.info("Re-enqueued processing for interview %s", interview.id)
    except Exception as exc:
        logger.error("Failed to re-enqueue interview %s: %s", interview.id, exc)
        interview.status = InterviewStatus.error
        interview.error_message = f"Failed to queue reprocessing: {exc}"

    return _serialize_interview(interview)


# ---------- Profile endpoints ----------

class ProfileOut(BaseModel):
    id: str
    interview_id: str
    name: str | None = None
    age_range: str | None = None
    role: str | None = None
    industry: str | None = None
    tech_level: str | None = None
    financial_context: str | None = None
    location: str | None = None
    notes: str | None = None
    missing_fields: list[str] | None = None
    user_filled: str


class ProfileUpdateIn(BaseModel):
    name: str | None = None
    age_range: str | None = None
    role: str | None = None
    industry: str | None = None
    tech_level: str | None = None
    financial_context: str | None = None
    location: str | None = None
    notes: str | None = None


def _serialize_profile(p: IntervieweeProfile) -> ProfileOut:
    return ProfileOut(
        id=str(p.id),
        interview_id=str(p.interview_id),
        name=p.name,
        age_range=p.age_range,
        role=p.role,

        industry=p.industry,
        tech_level=p.tech_level,
        financial_context=p.financial_context,
        location=p.location,
        notes=p.notes,
        missing_fields=p.missing_fields or [],
        user_filled=p.user_filled,
    )


@router.get("/{interview_id}/profile", response_model=ProfileOut)
async def get_profile(
    interview_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    """Get the interviewee profile for an interview."""
    result = await session.execute(
        select(IntervieweeProfile).where(IntervieweeProfile.interview_id == interview_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize_profile(profile)


@router.patch("/{interview_id}/profile", response_model=ProfileOut)
async def update_profile(
    interview_id: uuid.UUID,
    body: ProfileUpdateIn,
    session: AsyncSession = Depends(get_session),
) -> ProfileOut:
    """Fill in or correct profile fields (user-provided data)."""
    result = await session.execute(
        select(IntervieweeProfile).where(IntervieweeProfile.interview_id == interview_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    from app.services.profile_extractor import PROFILE_FIELDS
    still_missing = [f for f in PROFILE_FIELDS if not getattr(profile, f)]
    profile.missing_fields = still_missing
    profile.user_filled = "done" if not still_missing else "partial"

    await session.flush()
    await session.refresh(profile)
    return _serialize_profile(profile)
