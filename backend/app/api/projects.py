"""Project API endpoints."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Analysis,
    BoardStatus,
    Interview,
    IntervieweeProfile,
    InterviewStatus,
    Project,
    ProjectBoard,
    Report,
    get_session,
    async_session_factory,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ---------- Pydantic schemas ----------

class ProjectIn(BaseModel):
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    interview_count: int
    created_at: str
    updated_at: str


# ---------- Helpers ----------

def _serialize_project(project: Project, interview_count: int) -> ProjectOut:
    return ProjectOut(
        id=str(project.id),
        name=project.name,
        description=project.description,
        interview_count=interview_count,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


# ---------- Endpoints ----------

@router.get("", response_model=list[ProjectOut])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectOut]:
    """List all projects with interview counts."""
    projects_result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = projects_result.scalars().all()

    # Batch count interviews per project
    counts_result = await session.execute(
        select(Interview.project_id, func.count(Interview.id))
        .where(Interview.project_id.isnot(None))
        .group_by(Interview.project_id)
    )
    counts: dict[Any, int] = {str(row[0]): row[1] for row in counts_result}

    return [_serialize_project(p, counts.get(str(p.id), 0)) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectIn,
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    """Create a new project."""
    project = Project(name=body.name.strip(), description=body.description)
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return _serialize_project(project, 0)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    """Get a single project."""
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    count_result = await session.execute(
        select(func.count(Interview.id)).where(Interview.project_id == project_id)
    )
    count = count_result.scalar_one()
    return _serialize_project(project, count)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectIn,
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    """Update a project's name or description."""
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.name:
        project.name = body.name.strip()
    project.description = body.description

    await session.flush()
    await session.refresh(project)

    count_result = await session.execute(
        select(func.count(Interview.id)).where(Interview.project_id == project_id)
    )
    count = count_result.scalar_one()
    return _serialize_project(project, count)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a project (interviews become unassigned)."""
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(project)


# ---------- Research board ----------

class BoardOut(BaseModel):
    id: str | None = None
    project_id: str
    status: str
    error_message: str | None = None
    recurring_themes: list[dict[str, Any]] | None = None
    pain_points: list[dict[str, Any]] | None = None
    unique_insights: list[dict[str, Any]] | None = None
    patterns: list[dict[str, Any]] | None = None
    demographic_summary: dict[str, Any] | None = None
    data_gaps: list[dict[str, Any]] | None = None
    interviews_included: list[str] | None = None
    last_run_at: str | None = None


def _serialize_board(board: ProjectBoard) -> BoardOut:
    return BoardOut(
        id=str(board.id),
        project_id=str(board.project_id),
        status=board.status.value,
        error_message=board.error_message,
        recurring_themes=board.recurring_themes,
        pain_points=board.pain_points,
        unique_insights=board.unique_insights,
        patterns=board.patterns,
        demographic_summary=board.demographic_summary,
        data_gaps=board.data_gaps,
        interviews_included=board.interviews_included,
        last_run_at=board.last_run_at.isoformat() if board.last_run_at else None,
    )


@router.get("/{project_id}/board", response_model=BoardOut)
async def get_board(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> BoardOut:
    """Get the research board for a project (may not exist yet)."""
    result = await session.execute(
        select(ProjectBoard).where(ProjectBoard.project_id == project_id)
    )
    board = result.scalar_one_or_none()
    if board is None:
        # Return an empty pending board without persisting
        return BoardOut(project_id=str(project_id), status="pending")
    return _serialize_board(board)


@router.post("/{project_id}/board/synthesize", response_model=BoardOut)
async def synthesize_board(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> BoardOut:
    """Trigger cross-interview synthesis for the project research board."""
    proj_result = await session.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    board_result = await session.execute(
        select(ProjectBoard).where(ProjectBoard.project_id == project_id)
    )
    board = board_result.scalar_one_or_none()

    if board is None:
        board = ProjectBoard(project_id=project_id, status=BoardStatus.running)
        session.add(board)
    else:
        board.status = BoardStatus.running
        board.error_message = None

    await session.commit()  # commit NOW so the background task's new session can see the row
    await session.refresh(board)
    board_id = str(board.id)

    background_tasks.add_task(_run_board_synthesis, str(project_id), board_id)
    return _serialize_board(board)


async def _run_board_synthesis(project_id: str, board_id: str) -> None:
    """Background task: load all interviews and run cross-interview synthesis."""
    from app.services.board_synthesis import BoardSynthesisService

    async with async_session_factory() as session:
        try:
            # Load all completed interviews with their analysis, report, and profile
            result = await session.execute(
                select(Interview)
                .options(
                    selectinload(Interview.analysis),
                    selectinload(Interview.report),
                    selectinload(Interview.profile),
                )
                .where(
                    Interview.project_id == uuid.UUID(project_id),
                    Interview.status == InterviewStatus.complete,
                )
            )
            interviews = result.scalars().all()

            if not interviews:
                board_result = await session.execute(
                    select(ProjectBoard).where(ProjectBoard.id == uuid.UUID(board_id))
                )
                board = board_result.scalar_one()
                board.status = BoardStatus.error
                board.error_message = "No completed interviews found in this project."
                await session.commit()
                return

            iv_dicts = []
            for iv in interviews:
                profile_data = {}
                if iv.profile:
                    profile_data = {
                        "name": iv.profile.name,
                        "age_range": iv.profile.age_range,
                        "role": iv.profile.role,

                        "industry": iv.profile.industry,
                        "tech_level": iv.profile.tech_level,
                        "financial_context": iv.profile.financial_context,
                        "location": iv.profile.location,
                    }

                analysis_data = {}
                if iv.analysis:
                    analysis_data = {
                        "pain_points": iv.analysis.pain_points or [],
                        "goals": iv.analysis.goals or [],
                        "objections": iv.analysis.objections or [],
                        "feature_requests": iv.analysis.feature_requests or [],
                        "workarounds": iv.analysis.workarounds or [],
                        "emotional_moments": iv.analysis.emotional_moments or [],
                        "strong_quotes": iv.analysis.strong_quotes or [],
                    }

                iv_dicts.append({
                    "title": iv.title,
                    "profile": profile_data,
                    "analysis": analysis_data,
                    "report_summary": iv.report.executive_summary if iv.report else None,
                })

            svc = BoardSynthesisService()
            result_data = await svc.synthesize(iv_dicts)

            board_result = await session.execute(
                select(ProjectBoard).where(ProjectBoard.id == uuid.UUID(board_id))
            )
            board = board_result.scalar_one_or_none()
            if board is None:
                logger.error("Board %s not found after synthesis", board_id)
                return
            board.status = BoardStatus.complete
            board.recurring_themes = result_data.get("recurring_themes", [])
            board.pain_points = result_data.get("pain_points", [])
            board.unique_insights = result_data.get("unique_insights", [])
            board.patterns = result_data.get("patterns", [])
            board.demographic_summary = result_data.get("demographic_summary", {})
            board.data_gaps = result_data.get("data_gaps", [])
            board.interviews_included = [str(iv.id) for iv in interviews]
            board.last_run_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("Board synthesis complete for project %s", project_id)

        except Exception as exc:
            logger.exception("Board synthesis failed for project %s: %s", project_id, exc)
            try:
                board_result = await session.execute(
                    select(ProjectBoard).where(ProjectBoard.id == uuid.UUID(board_id))
                )
                board = board_result.scalar_one_or_none()
                if board is not None:
                    board.status = BoardStatus.error
                    board.error_message = str(exc)[:1000]
                    await session.commit()
            except Exception:
                logger.exception("Failed to update board error state")
