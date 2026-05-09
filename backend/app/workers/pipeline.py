"""arq worker pipeline for processing interview uploads."""

import logging
import uuid
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings
from app.models.database import (
    Analysis,
    FileType,
    Interview,
    IntervieweeProfile,
    InterviewStatus,
    Report,
    Transcript,
    async_session_factory,
)
from app.services.analysis import AnalysisService
from app.services.profile_extractor import ProfileExtractorService
from app.services.synthesis import SynthesisService
from app.services.transcript_parser import parse_transcript
from app.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)


def _parse_redis_url(url: str) -> RedisSettings:
    """Convert a redis:// URL into arq RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


async def get_arq_pool() -> ArqRedis:
    """Create an arq Redis connection pool."""
    return await create_pool(_parse_redis_url(settings.REDIS_URL))


async def process_interview(ctx: dict[str, Any], interview_id: str, synthesis_model: str = "haiku") -> None:
    """
    Main pipeline orchestrator.

    1. Load interview from DB
    2. If audio/video: transcribe -> save transcript -> update status
       If transcript file: parse file -> save transcript -> update status
    3. Run analysis extraction -> save analysis -> update status
    4. Run synthesis -> save report -> update status=complete
    5. Handle errors: update status=error, save error_message
    """
    logger.info("Starting pipeline for interview %s", interview_id)

    async with async_session_factory() as session:
        try:
            from sqlalchemy import select

            # 1. Load interview with existing relations
            result = await session.execute(
                select(Interview).where(Interview.id == uuid.UUID(interview_id))
            )
            interview = result.scalar_one_or_none()

            if interview is None:
                logger.error("Interview %s not found", interview_id)
                return

            # Load existing transcript/analysis/report
            existing_transcript = (await session.execute(
                select(Transcript).where(Transcript.interview_id == interview.id)
            )).scalar_one_or_none()

            existing_analysis = (await session.execute(
                select(Analysis).where(Analysis.interview_id == interview.id)
            )).scalar_one_or_none()

            existing_report = (await session.execute(
                select(Report).where(Report.interview_id == interview.id)
            )).scalar_one_or_none()

            # 2. Transcription — skip if already done
            transcript_data: dict[str, Any]

            if existing_transcript and existing_transcript.raw_text:
                logger.info("Skipping transcription — transcript already exists")
                transcript_data = {
                    "raw_text": existing_transcript.raw_text,
                    "segments": existing_transcript.segments or [],
                }
            else:
                if interview.file_type in (FileType.audio, FileType.video):
                    interview.status = InterviewStatus.transcribing
                    await session.commit()

                    svc = TranscriptionService()
                    transcript_data = await svc.transcribe(
                        interview.file_url, interview.file_type.value
                    )
                else:
                    transcript_data = parse_transcript(
                        interview.file_url, interview.file_type.value
                    )

                segments = transcript_data.get("segments", [])
                if segments and segments[0].get("language"):
                    interview.language_detected = segments[0]["language"]

                if existing_transcript:
                    existing_transcript.raw_text = transcript_data.get("raw_text", "")
                    existing_transcript.segments = transcript_data.get("segments", [])
                else:
                    session.add(Transcript(
                        interview_id=interview.id,
                        raw_text=transcript_data.get("raw_text", ""),
                        segments=transcript_data.get("segments", []),
                    ))
                await session.flush()

            segments = transcript_data.get("segments", [])

            # 3. Analysis — skip if already done
            analysis_data: dict[str, Any]

            if existing_analysis and existing_analysis.pain_points is not None:
                logger.info("Skipping analysis — analysis already exists")
                analysis_data = {
                    "pain_points": existing_analysis.pain_points or [],
                    "goals": existing_analysis.goals or [],
                    "objections": existing_analysis.objections or [],
                    "feature_requests": existing_analysis.feature_requests or [],
                    "workarounds": existing_analysis.workarounds or [],
                    "emotional_moments": existing_analysis.emotional_moments or [],
                    "strong_quotes": existing_analysis.strong_quotes or [],
                    "raw_extraction": existing_analysis.raw_extraction or [],
                }
            else:
                interview.status = InterviewStatus.analyzing
                await session.commit()

                analysis_svc = AnalysisService()
                analysis_data = await analysis_svc.extract_insights(segments)

                if existing_analysis:
                    for key in ["pain_points", "goals", "objections", "feature_requests",
                                "workarounds", "emotional_moments", "strong_quotes", "raw_extraction"]:
                        setattr(existing_analysis, key, analysis_data.get(key, []))
                else:
                    session.add(Analysis(
                        interview_id=interview.id,
                        pain_points=analysis_data.get("pain_points", []),
                        goals=analysis_data.get("goals", []),
                        objections=analysis_data.get("objections", []),
                        feature_requests=analysis_data.get("feature_requests", []),
                        workarounds=analysis_data.get("workarounds", []),
                        emotional_moments=analysis_data.get("emotional_moments", []),
                        strong_quotes=analysis_data.get("strong_quotes", []),
                        raw_extraction=analysis_data.get("raw_extraction", []),
                    ))
                await session.flush()

            # 4. Synthesis — always rerun (cheapest step, produces the report)
            interview.status = InterviewStatus.synthesizing
            await session.commit()

            synthesis_svc = SynthesisService()
            interview_dict = {
                "id": str(interview.id),
                "title": interview.title,
                "original_filename": interview.original_filename,
                "language_detected": interview.language_detected,
            }
            report_data = await synthesis_svc.synthesize_report(
                interview_dict, transcript_data, analysis_data, synthesis_model
            )

            if existing_report:
                existing_report.executive_summary = report_data.get("executive_summary", "")
                existing_report.detailed_findings = report_data.get("detailed_findings", {})
                existing_report.themes = report_data.get("themes", [])
                existing_report.recommendations = report_data.get("recommendations", [])
                existing_report.report_metadata = report_data.get("metadata", {})
            else:
                session.add(Report(
                    interview_id=interview.id,
                    executive_summary=report_data.get("executive_summary", ""),
                    detailed_findings=report_data.get("detailed_findings", {}),
                    themes=report_data.get("themes", []),
                    recommendations=report_data.get("recommendations", []),
                    report_metadata=report_data.get("metadata", {}),
                ))

            interview.status = InterviewStatus.complete

            # 5. Profile extraction — quick Claude call to pull structured participant info
            existing_profile = (await session.execute(
                select(IntervieweeProfile).where(IntervieweeProfile.interview_id == interview.id)
            )).scalar_one_or_none()

            try:
                profile_svc = ProfileExtractorService()
                raw_text = transcript_data.get("raw_text", "")
                profile_data = await profile_svc.extract(raw_text)

                if existing_profile:
                    # Merge: only fill in fields the user didn't already provide
                    for field in ["name", "age_range", "role", "industry",
                                  "tech_level", "financial_context", "location", "notes"]:
                        if not getattr(existing_profile, field) and profile_data.get(field):
                            setattr(existing_profile, field, profile_data[field])
                    from app.services.profile_extractor import PROFILE_FIELDS
                    existing_profile.missing_fields = [
                        f for f in PROFILE_FIELDS if not getattr(existing_profile, f)
                    ]
                    if existing_profile.user_filled == "no":
                        existing_profile.user_filled = "partial" if existing_profile.missing_fields else "done"
                else:
                    session.add(IntervieweeProfile(
                        interview_id=interview.id,
                        name=profile_data.get("name"),
                        age_range=profile_data.get("age_range"),
                        role=profile_data.get("role"),

                        industry=profile_data.get("industry"),
                        tech_level=profile_data.get("tech_level"),
                        financial_context=profile_data.get("financial_context"),
                        location=profile_data.get("location"),
                        notes=profile_data.get("notes"),
                        missing_fields=profile_data.get("missing_fields", []),
                        user_filled="no",
                    ))
            except Exception as profile_exc:
                logger.warning("Profile extraction failed (non-fatal): %s", profile_exc)

            await session.commit()

            logger.info("Pipeline complete for interview %s", interview_id)

        except Exception as exc:
            logger.exception("Pipeline failed for interview %s: %s", interview_id, exc)
            try:
                interview.status = InterviewStatus.error
                interview.error_message = str(exc)[:2000]
                await session.commit()
            except Exception:
                logger.exception("Failed to update error status for interview %s", interview_id)


class WorkerSettings:
    """arq worker configuration."""

    functions = [process_interview]
    redis_settings = _parse_redis_url(settings.REDIS_URL)
    max_jobs = 3
    job_timeout = 1800  # 30 minutes
    max_tries = 2
    health_check_interval = 30
