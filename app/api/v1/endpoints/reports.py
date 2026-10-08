from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_database, get_current_active_user
from app.models.user import User
from app.schemas.report import ReportCreate, ReportItemResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Complaints"])


@router.post(
    "",
    response_model=ReportItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a platform report or grievance",
    description="Allows authenticated candidates and recruiters to submit violation reports (e.g. fee demands, harassment, scams).",
)
async def create_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> ReportItemResponse:
    """Submit a moderation report for administrator review."""
    return await ReportService.create_report(
        db=db,
        current_user=current_user,
        payload=payload,
    )
