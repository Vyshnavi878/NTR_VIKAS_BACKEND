from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, or_, case, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report import Report
from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile


class ReportRepository:
    """Repository managing platform grievance and moderation reports in MySQL."""

    @classmethod
    async def get_next_report_number(cls, db: AsyncSession) -> str:
        """Generate the next consecutive unique human-readable report identifier (e.g. REP-000001)."""
        stmt = select(func.count(Report.id))
        result = await db.execute(stmt)
        count = result.scalar() or 0
        
        # Try count + 1 first
        next_num = count + 1
        candidate_number = f"REP-{next_num:06d}"
        
        # Check uniqueness just in case
        existing = await db.execute(select(Report.id).where(Report.report_number == candidate_number))
        if existing.scalar():
            # If collision occurs due to past deletions, find max sequence
            all_stmt = select(Report.report_number).order_by(Report.created_at.desc()).limit(100)
            res = await db.execute(all_stmt)
            numbers = res.scalars().all()
            max_val = count
            for n in numbers:
                if n and n.startswith("REP-"):
                    try:
                        val = int(n.replace("REP-", ""))
                        if val > max_val:
                            max_val = val
                    except ValueError:
                        pass
            candidate_number = f"REP-{max_val + 1:06d}"
            
        return candidate_number

    @classmethod
    async def create_report(
        cls,
        db: AsyncSession,
        report_type: str,
        reported_entity_type: str,
        reporter_user_id: str,
        description: str,
        reported_entity_id: Optional[str] = None,
        reported_user_id: Optional[str] = None,
        reported_user_type: str = "RECRUITER",
        reported_entity_name: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Report:
        """Create and persist a new report record."""
        report_number = await cls.get_next_report_number(db)
        
        report = Report(
            report_number=report_number,
            report_type=report_type,
            reported_user_type=reported_user_type.upper(),
            reported_user_id=reported_user_id,
            reported_entity_type=reported_entity_type.upper(),
            reported_entity_id=reported_entity_id,
            reported_entity_name=reported_entity_name,
            reporter_user_id=reporter_user_id,
            subject=subject,
            description=description,
            status="PENDING",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def get_by_id(cls, db: AsyncSession, report_id: str) -> Optional[Report]:
        """Fetch report by UUID ID or report number."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.reporter_user).selectinload(User.candidate_profile),
                selectinload(Report.reporter_user).selectinload(User.recruiter_profile),
                selectinload(Report.reported_user).selectinload(User.candidate_profile),
                selectinload(Report.reported_user).selectinload(User.recruiter_profile),
                selectinload(Report.resolved_by_admin),
                selectinload(Report.dismissed_by_admin),
            )
            .where(or_(Report.id == report_id, Report.report_number == report_id))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def list_reports(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        reported_user_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Report], int]:
        """Retrieve paginated list of reports matching filters."""
        query = select(Report).options(
            selectinload(Report.reporter_user).selectinload(User.candidate_profile),
            selectinload(Report.reporter_user).selectinload(User.recruiter_profile),
            selectinload(Report.reported_user).selectinload(User.candidate_profile),
            selectinload(Report.reported_user).selectinload(User.recruiter_profile),
            selectinload(Report.resolved_by_admin),
            selectinload(Report.dismissed_by_admin),
        )
        count_query = select(func.count(Report.id))

        filters = []

        if status and status.upper() != "ALL":
            filters.append(Report.status == status.upper())

        if reported_user_type and reported_user_type.upper() != "ALL":
            filters.append(Report.reported_user_type == reported_user_type.upper())

        if search and search.strip():
            s = f"%{search.strip()}%"
            filters.append(
                or_(
                    Report.report_number.ilike(s),
                    Report.report_type.ilike(s),
                    Report.subject.ilike(s),
                    Report.description.ilike(s),
                    Report.reported_entity_name.ilike(s),
                    Report.admin_notes.ilike(s),
                    Report.resolution_reason.ilike(s),
                )
            )

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        # Sorting
        order_col = getattr(Report, sort_by, Report.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(order_col))
        else:
            query = query.order_by(desc(order_col))

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = result.scalars().all()

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        return list(items), total

    @classmethod
    async def get_summary_counts(cls, db: AsyncSession) -> Dict[str, int]:
        """Aggregate report counts grouped by moderation status."""
        stmt = select(
            func.count(Report.id).label("total"),
            func.sum(case((Report.status == "PENDING", 1), else_=0)).label("pending"),
            func.sum(case((Report.status == "RESOLVED", 1), else_=0)).label("resolved"),
            func.sum(case((Report.status == "DISMISSED", 1), else_=0)).label("dismissed"),
        )
        result = await db.execute(stmt)
        row = result.one_or_none()

        total = row.total if row and row.total else 0
        pending = int(row.pending) if row and row.pending else 0
        resolved = int(row.resolved) if row and row.resolved else 0
        dismissed = int(row.dismissed) if row and row.dismissed else 0

        return {
            "all": total,
            "pending": pending,
            "resolved": resolved,
            "dismissed": dismissed,
            "open_complaints": pending,
        }

    @classmethod
    async def get_all_for_export(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        reported_user_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Report]:
        """Fetch all reports matching filters for CSV generation."""
        query = select(Report).options(
            selectinload(Report.reporter_user).selectinload(User.candidate_profile),
            selectinload(Report.reporter_user).selectinload(User.recruiter_profile),
            selectinload(Report.reported_user).selectinload(User.candidate_profile),
            selectinload(Report.reported_user).selectinload(User.recruiter_profile),
        )

        filters = []
        if status and status.upper() != "ALL":
            filters.append(Report.status == status.upper())

        if reported_user_type and reported_user_type.upper() != "ALL":
            filters.append(Report.reported_user_type == reported_user_type.upper())

        if search and search.strip():
            s = f"%{search.strip()}%"
            filters.append(
                or_(
                    Report.report_number.ilike(s),
                    Report.report_type.ilike(s),
                    Report.subject.ilike(s),
                    Report.description.ilike(s),
                    Report.reported_entity_name.ilike(s),
                )
            )

        if filters:
            for f in filters:
                query = query.where(f)

        query = query.order_by(Report.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
