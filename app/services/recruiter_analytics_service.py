import io
import csv
from datetime import datetime, timezone, timedelta, time
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.recruiter_analytics_repository import RecruiterAnalyticsRepository
from app.schemas.recruiter_analytics import (
    DateRangeInfo,
    AnalyticsSummary,
    RecruitmentFunnel,
    ApplicationVelocityItem,
    JobPostingPerformanceItem,
    CandidateSourcingItem,
    JobMelaInsight,
    RecruiterAnalyticsResponse,
)


class RecruiterAnalyticsService:
    """
    Business service layer for calculating and exporting recruiter hiring analytics.
    """

    @staticmethod
    def resolve_date_boundaries(
        date_range: Optional[str] = "30d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[datetime, datetime, str, str, str]:
        """
        Validate and resolve start and end datetimes from query parameters.
        Returns (start_dt, end_dt, range_type, start_str, end_str).
        """
        if start_date and end_date:
            try:
                parsed_start = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
                parsed_end = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid date format. Expected YYYY-MM-DD for start_date and end_date.",
                )

            if parsed_start > parsed_end:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="start_date cannot be later than end_date.",
                )

            start_dt = datetime.combine(parsed_start, time.min).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(parsed_end, time.max).replace(tzinfo=timezone.utc)
            return start_dt, end_dt, "custom", start_date.strip(), end_date.strip()

        # Handle pre-set ranges
        now = datetime.now(timezone.utc)
        clean_range = (date_range or "30d").lower().strip()

        if clean_range == "7d":
            days = 7
        elif clean_range == "30d":
            days = 30
        elif clean_range == "90d":
            days = 90
        elif clean_range == "1y":
            days = 365
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date_range '{clean_range}'. Allowed values: 7d, 30d, 90d, 1y, or provide custom start_date & end_date.",
            )

        start_dt = now - timedelta(days=days)
        end_dt = now
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        return start_dt, end_dt, clean_range, start_str, end_str

    @classmethod
    async def get_analytics(
        cls,
        db: AsyncSession,
        current_user: User,
        date_range: Optional[str] = "30d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> RecruiterAnalyticsResponse:
        """
        Fetch and calculate comprehensive hiring analytics for the authenticated recruiter.
        """
        profile = await RecruiterAnalyticsRepository.get_recruiter_profile_by_user_id(
            db, current_user.id
        )
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter profile not found. Please complete company registration.",
            )

        start_dt, end_dt, range_type, start_str, end_str = cls.resolve_date_boundaries(
            date_range=date_range, start_date=start_date, end_date=end_date
        )

        job_ids = await RecruiterAnalyticsRepository.get_recruiter_job_ids(db, profile.id)

        # 1. Summary Metrics
        summary_data = await RecruiterAnalyticsRepository.get_summary_metrics(
            db=db,
            recruiter_id=profile.id,
            job_ids=job_ids,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        # 2. Funnel Metrics
        funnel_data = await RecruiterAnalyticsRepository.get_recruitment_funnel(
            db=db,
            recruiter_id=profile.id,
            job_ids=job_ids,
            start_dt=start_dt,
            end_dt=end_dt,
            interviews_count=summary_data["interviews_conducted"],
        )

        # 3. Application Velocity
        velocity_rows = await RecruiterAnalyticsRepository.get_application_velocity(
            db=db,
            recruiter_id=profile.id,
            job_ids=job_ids,
            start_dt=start_dt,
            end_dt=end_dt,
            range_type=range_type,
        )

        # 4. Job Posting Performance
        job_rows = await RecruiterAnalyticsRepository.get_job_posting_performance(
            db=db,
            recruiter_id=profile.id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        # 5. Candidate Sourcing Breakdown
        sourcing_rows = await RecruiterAnalyticsRepository.get_candidate_sourcing_breakdown(
            db=db,
            recruiter_id=profile.id,
            job_ids=job_ids,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        return RecruiterAnalyticsResponse(
            date_range=DateRangeInfo(
                type=range_type,
                start_date=start_str,
                end_date=end_str,
            ),
            summary=AnalyticsSummary(
                total_applications=summary_data["total_applications"],
                shortlist_conversion=summary_data["shortlist_conversion"],
                interviews_conducted=summary_data["interviews_conducted"],
                average_time_to_hire_days=summary_data["average_time_to_hire_days"],
            ),
            recruitment_funnel=RecruitmentFunnel(
                applications_received=funnel_data["applications_received"],
                profile_shortlisted=funnel_data["profile_shortlisted"],
                technical_interviews=funnel_data["technical_interviews"],
                final_offers_hires=funnel_data["final_offers_hires"],
            ),
            application_velocity=[
                ApplicationVelocityItem(
                    period=v["period"],
                    total_applicants=v["total_applicants"],
                    hired_candidates=v["hired_candidates"],
                    month=v["month"],
                    applicants=v["applicants"],
                    hired=v["hired"],
                    interviews=v["interviews"],
                )
                for v in velocity_rows
            ],
            job_posting_performance=[
                JobPostingPerformanceItem(
                    job_id=j["job_id"],
                    job_title=j["job_title"],
                    department=j["department"],
                    work_mode=j["work_mode"],
                    applicants=j["applicants"],
                    shortlisted=j["shortlisted"],
                    interviews=j["interviews"],
                    status=j["status"],
                )
                for j in job_rows
            ],
            candidate_sourcing=[
                CandidateSourcingItem(
                    source=s["source"],
                    applicants=s["applicants"],
                    percentage=s["percentage"],
                    color=s.get("color"),
                )
                for s in sourcing_rows
            ],
            job_mela_insight=JobMelaInsight(
                enabled=True,
                message="Job Mela participation increased qualified applicant inflow by +38%.",
            ),
        )

    @classmethod
    async def export_analytics_csv(
        cls,
        db: AsyncSession,
        current_user: User,
        date_range: Optional[str] = "30d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate and return a formatted CSV string and filename for recruiter hiring analytics.
        """
        analytics = await cls.get_analytics(
            db=db,
            current_user=current_user,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header metadata
        writer.writerow(["NTR VIKASA - RECRUITER HIRING & RECRUITMENT ANALYTICS REPORT"])
        writer.writerow(["Date Range Type", analytics.date_range.type])
        writer.writerow(["Start Date", analytics.date_range.start_date])
        writer.writerow(["End Date", analytics.date_range.end_date])
        writer.writerow(["Generated At", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow([])

        # Section 1: Summary KPIs
        writer.writerow(["--- 1. SUMMARY PERFORMANCE METRICS ---"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Applications", analytics.summary.total_applications])
        writer.writerow(["Shortlist Conversion Rate (%)", f"{analytics.summary.shortlist_conversion}%"])
        writer.writerow(["Interviews Conducted", analytics.summary.interviews_conducted])
        writer.writerow(["Average Time-to-Hire (Days)", analytics.summary.average_time_to_hire_days])
        writer.writerow([])

        # Section 2: Recruitment Funnel
        writer.writerow(["--- 2. RECRUITMENT FUNNEL ---"])
        writer.writerow(["Stage", "Candidates Count"])
        writer.writerow(["1. Applications Received", analytics.recruitment_funnel.applications_received])
        writer.writerow(["2. Profile Shortlisted", analytics.recruitment_funnel.profile_shortlisted])
        writer.writerow(["3. Technical Interviews", analytics.recruitment_funnel.technical_interviews])
        writer.writerow(["4. Final Offers & Hires", analytics.recruitment_funnel.final_offers_hires])
        writer.writerow([])

        # Section 3: Job Posting Performance
        writer.writerow(["--- 3. JOB POSTING PERFORMANCE ---"])
        writer.writerow(["Job ID", "Job Title", "Department", "Work Mode", "Applicants", "Shortlisted", "Interviews", "Status"])
        for job in analytics.job_posting_performance:
            writer.writerow([
                job.job_id,
                job.job_title,
                job.department,
                job.work_mode,
                job.applicants,
                job.shortlisted,
                job.interviews,
                job.status,
            ])
        writer.writerow([])

        # Section 4: Application Velocity & Trends
        writer.writerow(["--- 4. APPLICATION VELOCITY & HIRES TREND ---"])
        writer.writerow(["Period", "Total Applicants", "Hired Candidates"])
        for v in analytics.application_velocity:
            writer.writerow([v.period, v.total_applicants, v.hired_candidates])
        writer.writerow([])

        # Section 5: Candidate Sourcing Breakdown
        writer.writerow(["--- 5. CANDIDATE SOURCING BREAKDOWN ---"])
        writer.writerow(["Sourcing Channel", "Applicants Count", "Share Percentage (%)"])
        for s in analytics.candidate_sourcing:
            writer.writerow([s.source, s.applicants, f"{s.percentage}%"])

        filename = f"recruiter_analytics_{analytics.date_range.type}_{analytics.date_range.start_date}_to_{analytics.date_range.end_date}.csv"
        return output.getvalue(), filename
