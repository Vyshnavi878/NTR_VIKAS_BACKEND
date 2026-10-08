import csv
import io
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.report import Report
from app.models.job import Job
from app.models.internship import Internship
from app.models.job_mela import JobMela
from app.models.candidate import CandidateProfile
from app.models.recruiter import RecruiterProfile
from app.models.notification import Notification
from app.repositories.report_repository import ReportRepository
from app.services.audit_service import AuditService
from app.schemas.report import (
    ReportCreate,
    ReportResolveRequest,
    ReportDismissRequest,
    ReportItemResponse,
    ReportDetailResponse,
    ReportListResponse,
    ReportSummaryResponse,
    ReportActionResponse,
    ReportEntityInfo,
    ReporterInfo,
    ReportedUserInfo,
)

REPORT_TYPE_LABELS: Dict[str, str] = {
    "JOB_SCAM": "Job Scam / Fee Request",
    "MISLEADING_JOB_DESCRIPTION": "Misleading Job Description",
    "PROFILE_HARASSMENT": "Profile Harassment in Messages",
    "SPAM": "Spam Content",
    "FRAUD": "Fraudulent Activity",
    "FEE_REQUEST": "Illegal Fee Demand",
    "INAPPROPRIATE_CONTENT": "Inappropriate Content",
    "FAKE_RECRUITER": "Unverified / Fake Recruiter",
    "FAKE_CANDIDATE": "Fake / Suspicious Candidate",
    "OTHER": "Other Violation",
}


class ReportService:
    """Business logic and moderation workflows for platform reports and grievances."""

    @classmethod
    def get_report_type_label(cls, report_type: str) -> str:
        """Convert enum or raw report type to a user-friendly UI display label."""
        normalized = report_type.strip().upper().replace(" ", "_").replace("/", "_").replace("-", "_")
        for key, label in REPORT_TYPE_LABELS.items():
            if normalized == key or normalized in key or key in normalized:
                return label
        return report_type.title() if "_" in report_type else report_type

    @classmethod
    def format_report_item(cls, report: Report) -> ReportItemResponse:
        """Transform SQLAlchemy Report model to structured Pydantic response."""
        # 1. Reporter Info
        reporter_name = "Platform User"
        reporter_email = None
        reporter_user_type = "CANDIDATE"
        if report.reporter_user:
            reporter_email = report.reporter_user.email
            reporter_user_type = report.reporter_user.role
            if report.reporter_user.candidate_profile and report.reporter_user.candidate_profile.name:
                reporter_name = report.reporter_user.candidate_profile.name
            elif report.reporter_user.recruiter_profile and report.reporter_user.recruiter_profile.recruiter_name:
                reporter_name = report.reporter_user.recruiter_profile.recruiter_name
            elif report.reporter_user.email:
                reporter_name = report.reporter_user.email.split("@")[0].replace(".", " ").title()

        reporter_info = ReporterInfo(
            id=report.reporter_user_id,
            name=reporter_name,
            email=reporter_email,
            user_type=reporter_user_type,
        )

        # 2. Reported User Info (if available)
        reported_user_info = None
        if report.reported_user:
            reported_u_name = report.reported_user.email.split("@")[0].replace(".", " ").title()
            if report.reported_user.candidate_profile and report.reported_user.candidate_profile.name:
                reported_u_name = report.reported_user.candidate_profile.name
            elif report.reported_user.recruiter_profile and report.reported_user.recruiter_profile.recruiter_name:
                reported_u_name = report.reported_user.recruiter_profile.recruiter_name

            reported_user_info = ReportedUserInfo(
                id=report.reported_user_id,
                name=reported_u_name,
                email=report.reported_user.email,
                user_type=report.reported_user.role,
            )

        # 3. Reported Entity Info
        entity_name = report.reported_entity_name or "Target Entity"
        reported_entity_info = ReportEntityInfo(
            type=report.reported_user_type,
            name=entity_name,
            id=report.reported_entity_id or report.report_number,
        )

        # 4. Action taken & formatted dates
        action_taken = report.admin_notes
        if not action_taken:
            if report.status == "RESOLVED":
                action_taken = "Corrective action taken by administrator."
            elif report.status == "DISMISSED":
                action_taken = "Dismissed as non-actionable."
            else:
                action_taken = "Under active moderator investigation."

        date_str = report.created_at.strftime("%Y-%m-%d") if report.created_at else None

        return ReportItemResponse(
            id=report.id,
            report_number=report.report_number,
            report_type=report.report_type,
            report_type_label=cls.get_report_type_label(report.report_type),
            reported_entity=reported_entity_info,
            reported_user_type=report.reported_user_type,
            reported_user=reported_user_info,
            reporter=reporter_info,
            subject=report.subject,
            description=report.description,
            details=report.description,
            reason=report.description,
            date=date_str,
            status=report.status,
            action_taken=action_taken,
            admin_notes=report.admin_notes,
            resolution_reason=report.resolution_reason,
            resolved_at=report.resolved_at,
            dismissed_at=report.dismissed_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    @classmethod
    async def create_report(
        cls,
        db: AsyncSession,
        current_user: User,
        payload: ReportCreate,
    ) -> ReportItemResponse:
        """Handle submission of a grievance / report from an authenticated platform user."""
        reported_entity_name = payload.reported_entity_name
        reported_user_id = payload.reported_user_id
        reported_user_type = (payload.reported_user_type or "RECRUITER").upper()
        reported_entity_type = (payload.reported_entity_type or "JOB").upper()

        # Try to resolve related entity if applicable
        if reported_entity_type == "JOB" and payload.reported_entity_id:
            job_res = await db.execute(
                select(Job).where(
                    (Job.id == payload.reported_entity_id) | (Job.job_id == payload.reported_entity_id) | (Job.job_number == payload.reported_entity_id)
                )
            )
            job = job_res.scalar_one_or_none()
            if job:
                if not reported_entity_name:
                    reported_entity_name = f"{job.company_name} ({job.title})"
                reported_user_type = "RECRUITER"
                # If recruiter relation exists, fetch user_id
                if not reported_user_id and job.recruiter_id:
                    rec_res = await db.execute(select(RecruiterProfile.user_id).where(RecruiterProfile.id == job.recruiter_id))
                    reported_user_id = rec_res.scalar()

        elif reported_entity_type == "INTERNSHIP" and payload.reported_entity_id:
            intern_res = await db.execute(
                select(Internship).where(
                    (Internship.id == payload.reported_entity_id) | (Internship.internship_number == payload.reported_entity_id)
                )
            )
            intern = intern_res.scalar_one_or_none()
            if intern:
                if not reported_entity_name:
                    reported_entity_name = f"{intern.title} ({intern.duration})"
                reported_user_type = "RECRUITER"
                if not reported_user_id and intern.company_id:
                    rec_res = await db.execute(select(RecruiterProfile.user_id).where(RecruiterProfile.id == intern.company_id))
                    reported_user_id = rec_res.scalar()

        elif reported_entity_type == "JOB_MELA" and payload.reported_entity_id:
            mela_res = await db.execute(
                select(JobMela).where(
                    (JobMela.id == payload.reported_entity_id) | (JobMela.mela_number == payload.reported_entity_id)
                )
            )
            mela = mela_res.scalar_one_or_none()
            if mela and not reported_entity_name:
                reported_entity_name = mela.title

        elif reported_entity_type in ["CANDIDATE", "CANDIDATE_PROFILE"]:
            reported_user_type = "CANDIDATE"
            if payload.reported_entity_id and not reported_user_id:
                cand_res = await db.execute(
                    select(CandidateProfile).where(
                        (CandidateProfile.id == payload.reported_entity_id) | (CandidateProfile.user_id == payload.reported_entity_id)
                    )
                )
                cand = cand_res.scalar_one_or_none()
                if cand:
                    reported_user_id = cand.user_id
                    if not reported_entity_name:
                        reported_entity_name = cand.name

        if not reported_entity_name:
            reported_entity_name = f"{reported_entity_type.title()} #{payload.reported_entity_id or 'General'}"

        report = await ReportRepository.create_report(
            db=db,
            report_type=payload.report_type,
            reported_entity_type=reported_entity_type,
            reporter_user_id=current_user.id,
            description=payload.description,
            reported_entity_id=payload.reported_entity_id,
            reported_user_id=reported_user_id,
            reported_user_type=reported_user_type,
            reported_entity_name=reported_entity_name,
            subject=payload.subject,
        )

        # Refresh with relations
        detailed_report = await ReportRepository.get_by_id(db, report.id)
        return cls.format_report_item(detailed_report or report)

    @classmethod
    async def list_reports(
        cls,
        db: AsyncSession,
        current_admin: User,
        status_filter: Optional[str] = None,
        reported_user_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> ReportListResponse:
        """List reports with moderation status filtering, entity filtering, and search."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        items, total = await ReportRepository.list_reports(
            db=db,
            status=status_filter,
            reported_user_type=reported_user_type,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        formatted_items = [cls.format_report_item(r) for r in items]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return ReportListResponse(
            items=formatted_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    @classmethod
    async def get_summary(cls, db: AsyncSession, current_admin: User) -> ReportSummaryResponse:
        """Get summary count cards for the moderation dashboard."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        counts = await ReportRepository.get_summary_counts(db)
        return ReportSummaryResponse(**counts)

    @classmethod
    async def get_report_detail(
        cls,
        db: AsyncSession,
        current_admin: User,
        report_id: str,
    ) -> ReportDetailResponse:
        """Retrieve full details of an individual grievance report."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        report = await ReportRepository.get_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report #{report_id} not found.",
            )

        return cls.format_report_item(report)

    @classmethod
    async def resolve_report(
        cls,
        db: AsyncSession,
        current_admin: User,
        report_id: str,
        payload: ReportResolveRequest,
    ) -> ReportActionResponse:
        """Mark a pending grievance report as RESOLVED and log immutable audit event."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        report = await ReportRepository.get_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report #{report_id} not found.",
            )

        if report.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This report has already been {report.status.lower()}.",
            )

        notes = payload.admin_notes or "Reviewed evidence. Corrective action enforced against reported entity."
        reason = payload.resolution_reason or "POLICY_VIOLATION_CONFIRMED"

        report.status = "RESOLVED"
        report.admin_notes = notes
        report.resolution_reason = reason
        report.resolved_by_admin_id = current_admin.id
        report.resolved_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)

        # Notify reporter if candidate
        if report.reporter_user and report.reporter_user.candidate_profile:
            cand_profile_id = report.reporter_user.candidate_profile.id
            notif = Notification(
                candidate_id=cand_profile_id,
                category="MODERATION",
                title=f"Report {report.report_number} Resolved",
                message=f"Your complaint regarding {report.reported_entity_name or 'the entity'} has been reviewed and resolved by Trust & Safety moderators.",
                link="/candidate/dashboard",
            )
            db.add(notif)

        await db.commit()
        await db.refresh(report)

        # Audit Trail
        await AuditService.log_event(
            db=db,
            actor=current_admin.email,
            action="REPORT_RESOLVED",
            entity="REPORT",
            entity_id=report.report_number,
            target_name=f"{report.reported_entity_name or 'Entity'} ({report.report_number})",
            result="SUCCESS",
            metadata={
                "report_id": report.id,
                "report_number": report.report_number,
                "report_type": report.report_type,
                "resolution_reason": reason,
                "admin_notes": notes,
            },
        )

        detailed = await ReportRepository.get_by_id(db, report.id)
        return ReportActionResponse(
            message=f"Report {report.report_number} resolved successfully.",
            report=cls.format_report_item(detailed or report),
        )

    @classmethod
    async def dismiss_report(
        cls,
        db: AsyncSession,
        current_admin: User,
        report_id: str,
        payload: ReportDismissRequest,
    ) -> ReportActionResponse:
        """Mark a pending grievance report as DISMISSED and record audit log."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        report = await ReportRepository.get_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report #{report_id} not found.",
            )

        if report.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This report has already been {report.status.lower()}.",
            )

        notes = payload.admin_notes or "Dismissed as non-actionable or insufficient evidence."
        reason = payload.resolution_reason or "INSUFFICIENT_EVIDENCE"

        report.status = "DISMISSED"
        report.admin_notes = notes
        report.resolution_reason = reason
        report.dismissed_by_admin_id = current_admin.id
        report.dismissed_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)

        # Notify reporter if candidate
        if report.reporter_user and report.reporter_user.candidate_profile:
            cand_profile_id = report.reporter_user.candidate_profile.id
            notif = Notification(
                candidate_id=cand_profile_id,
                category="MODERATION",
                title=f"Report {report.report_number} Reviewed",
                message=f"Your complaint regarding {report.reported_entity_name or 'the entity'} has been reviewed and dismissed as non-actionable.",
                link="/candidate/dashboard",
            )
            db.add(notif)

        await db.commit()
        await db.refresh(report)

        # Audit Trail
        await AuditService.log_event(
            db=db,
            actor=current_admin.email,
            action="REPORT_DISMISSED",
            entity="REPORT",
            entity_id=report.report_number,
            target_name=f"{report.reported_entity_name or 'Entity'} ({report.report_number})",
            result="SUCCESS",
            metadata={
                "report_id": report.id,
                "report_number": report.report_number,
                "report_type": report.report_type,
                "resolution_reason": reason,
                "admin_notes": notes,
            },
        )

        detailed = await ReportRepository.get_by_id(db, report.id)
        return ReportActionResponse(
            message=f"Report {report.report_number} dismissed successfully.",
            report=cls.format_report_item(detailed or report),
        )

    @classmethod
    async def export_reports_csv(
        cls,
        db: AsyncSession,
        current_admin: User,
        status_filter: Optional[str] = None,
        reported_user_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """Stream downloadable CSV export of platform reports and moderation actions."""
        if current_admin.role.upper() not in ["ADMIN", "PLATFORM_ADMINISTRATOR", "SUPER_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required.",
            )

        reports = await ReportRepository.get_all_for_export(
            db=db,
            status=status_filter,
            reported_user_type=reported_user_type,
            search=search,
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Report Number",
            "Report Type",
            "Reported User Type",
            "Reported Entity",
            "Reporter",
            "Reporter Email",
            "Subject",
            "Description / Reason",
            "Date",
            "Status",
            "Action Taken / Notes",
            "Resolution Reason",
        ])

        for r in reports:
            item = cls.format_report_item(r)
            writer.writerow([
                item.report_number,
                item.report_type_label,
                item.reported_user_type.capitalize(),
                item.reported_entity.name,
                item.reporter.name,
                item.reporter.email or "N/A",
                item.subject or "N/A",
                item.description or item.details or "N/A",
                item.date or "N/A",
                item.status,
                item.action_taken or item.admin_notes or "N/A",
                item.resolution_reason or "N/A",
            ])

        # Audit Trail
        await AuditService.log_event(
            db=db,
            actor=current_admin.email,
            action="ADMIN_REPORTS_EXPORT",
            entity="REPORT",
            entity_id="ALL",
            target_name="Platform Reports & Complaints CSV Export",
            result="SUCCESS",
            metadata={
                "status_filter": status_filter,
                "user_type_filter": reported_user_type,
                "search": search,
                "record_count": len(reports),
            },
        )

        return output.getvalue()
