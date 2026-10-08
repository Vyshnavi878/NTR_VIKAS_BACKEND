import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.admin_analytics import (
    AdminAnalyticsResponse,
    AnalyticsPeriod,
)
from app.repositories.admin_analytics_repository import AdminAnalyticsRepository
from app.services.audit_service import AuditService


class AdminAnalyticsService:
    """Centralized service for managing and calculating platform-wide analytics."""

    @staticmethod
    def _parse_date_range(
        period: Optional[str] = "30d",
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None,
    ) -> Tuple[datetime, datetime, str, str]:
        """
        Parses and validates time range parameters into UTC datetime objects.
        """
        now = datetime.now(timezone.utc)
        p = (period or "30d").lower().strip()

        if p == "7d":
            start_dt = now - timedelta(days=7)
            end_dt = now
            label = "Last 7 Days"
        elif p == "30d":
            start_dt = now - timedelta(days=30)
            end_dt = now
            label = "Last 30 Days"
        elif p == "90d":
            start_dt = now - timedelta(days=90)
            end_dt = now
            label = "Last 90 Days"
        elif p in ["1y", "365d"]:
            start_dt = now - timedelta(days=365)
            end_dt = now
            label = "Last 1 Year"
        elif p == "custom":
            if not start_date_str or not end_date_str:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Please provide both start_date and end_date for custom range.",
                )
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid date format. Expected YYYY-MM-DD.",
                )

            if start_dt > end_dt:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="From Date cannot be after To Date.",
                )

            label = f"{start_date_str} – {end_date_str}"
        else:
            # Default fallback to 30d
            start_dt = now - timedelta(days=30)
            end_dt = now
            label = "Last 30 Days"
            p = "30d"

        return start_dt, end_dt, p, label

    @classmethod
    async def get_analytics(
        cls,
        db: AsyncSession,
        current_admin: User,
        period: Optional[str] = "30d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AdminAnalyticsResponse:
        """
        Fetches platform-wide aggregate metrics, sector distributions, and monthly trajectory.
        Requires Administrator authorization.
        """
        if current_admin.role not in [
            "ADMIN",
            "PLATFORM_ADMINISTRATOR",
            "Platform Administrator",
            "Super Admin",
            "SUPER_ADMIN",
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform Administrator authorization required to view platform analytics.",
            )

        start_dt, end_dt, period_type, period_label = cls._parse_date_range(
            period=period,
            start_date_str=start_date,
            end_date_str=end_date,
        )

        kpis = await AdminAnalyticsRepository.get_kpis(db, start_dt, end_dt)
        sectors = await AdminAnalyticsRepository.get_hiring_demand_by_sector(db, start_dt, end_dt)
        trajectory = await AdminAnalyticsRepository.get_monthly_placement_trajectory(db, start_dt, end_dt)

        return AdminAnalyticsResponse(
            period=AnalyticsPeriod(
                type=period_type,
                start_date=start_dt.strftime("%Y-%m-%d"),
                end_date=end_dt.strftime("%Y-%m-%d"),
                label=period_label,
            ),
            kpis=kpis,
            hiring_demand_by_sector=sectors,
            monthly_placement_trajectory=trajectory,
        )

    @classmethod
    async def export_analytics_csv(
        cls,
        db: AsyncSession,
        current_admin: User,
        period: Optional[str] = "30d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Generates downloadable CSV report and creates an audit log entry.
        """
        analytics = await cls.get_analytics(
            db=db,
            current_admin=current_admin,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # 1. Report Header
        writer.writerow(["NTR VIKASA STATE JOB PORTAL - PLATFORM HIRING ANALYTICS REPORT"])
        writer.writerow(["Report Period", analytics.period.label])
        writer.writerow(["Date Range", f"{analytics.period.start_date} to {analytics.period.end_date}"])
        writer.writerow(["Generated At", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow(["Generated By", current_admin.email])
        writer.writerow([])

        # 2. KPI Metrics Summary
        writer.writerow(["--- PLATFORM SCALE KPIS ---"])
        writer.writerow(["Metric", "Count"])
        writer.writerow(["Total Platform Users", analytics.kpis.total_platform_users])
        writer.writerow(["Active Candidates", analytics.kpis.active_candidates])
        writer.writerow(["Verified Recruiters", analytics.kpis.verified_recruiters])
        writer.writerow(["Registered Companies", analytics.kpis.registered_companies])
        writer.writerow(["Live Posted Jobs", analytics.kpis.live_posted_jobs])
        writer.writerow(["Submitted Applications", analytics.kpis.submitted_applications])
        writer.writerow(["Active Internships", analytics.kpis.active_internships])
        writer.writerow(["Job Mela Registrations", analytics.kpis.mela_registrations])
        writer.writerow([])

        # 3. Hiring Demand by Industry Sector
        writer.writerow(["--- HIRING DEMAND BY INDUSTRY SECTOR ---"])
        writer.writerow(["Industry Sector", "Live Jobs", "Share Percentage"])
        for sector in analytics.hiring_demand_by_sector:
            writer.writerow([sector.name, sector.job_count, f"{sector.percentage}%"])
        writer.writerow([])

        # 4. Monthly Platform Placement Trajectory
        writer.writerow(["--- MONTHLY PLATFORM PLACEMENT TRAJECTORY ---"])
        writer.writerow(["Month", "Candidates", "Active Jobs", "Placements"])
        for m in analytics.monthly_placement_trajectory:
            writer.writerow([m.month, m.candidates, m.active_jobs, m.placements])

        # Record Audit Log
        await AuditService.log_event(
            db=db,
            actor=current_admin.email,
            action="ADMIN_ANALYTICS_EXPORT",
            entity="ANALYTICS",
            entity_id=analytics.period.type.upper(),
            target_name="Platform Hiring Analytics Report",
            result="SUCCESS",
            metadata={
                "period": analytics.period.type,
                "start_date": analytics.period.start_date,
                "end_date": analytics.period.end_date,
            },
        )

        return output.getvalue()
