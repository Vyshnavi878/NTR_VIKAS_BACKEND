import re
import uuid
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.candidate import CandidateProfile
from app.models.candidate_settings import CandidateSettings
from app.models.candidate_profile_details import CandidateEducation
from app.schemas.admin_candidate import AdminCreateCandidateRequest


def compute_aadhaar_hash(raw_aadhaar: str) -> str:
    clean = re.sub(r"\D", "", raw_aadhaar or "")
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def mask_aadhaar(raw_aadhaar: str) -> str:
    clean = re.sub(r"\D", "", raw_aadhaar or "")
    if len(clean) >= 4:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"


class AdminCandidateRepository:
    """
    Async database repository layer for administrator Candidate governance.
    Direct MySQL persistence using SQLAlchemy 2.0 AsyncSession.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        clean = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == clean)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        clean = re.sub(r"[^\d+]", "", phone.strip())
        digits = re.sub(r"\D", "", clean)
        stmt = select(User).where(
            or_(
                User.phone == clean,
                User.phone == digits,
                User.phone.like(f"%{digits[-10:]}"),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_candidate_by_aadhaar(
        db: AsyncSession,
        aadhaar_number: str,
        aadhaar_hash: Optional[str] = None,
    ) -> Optional[CandidateProfile]:
        clean = re.sub(r"\D", "", aadhaar_number.strip())
        fingerprint = aadhaar_hash or compute_aadhaar_hash(clean)
        stmt = select(CandidateProfile).where(
            or_(
                CandidateProfile.aadhaar_number == clean,
                CandidateProfile.aadhaar_hash == fingerprint,
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_candidate_by_id(db: AsyncSession, candidate_id: str) -> Optional[Tuple[CandidateProfile, User]]:
        stmt = (
            select(CandidateProfile, User)
            .join(User, CandidateProfile.user_id == User.id)
            .where(
                or_(
                    CandidateProfile.id == candidate_id,
                    CandidateProfile.user_id == candidate_id,
                )
            )
        )
        result = await db.execute(stmt)
        row = result.first()
        if row:
            return row[0], row[1]
        return None

    @classmethod
    async def get_admin_candidates(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        placement_status: Optional[str] = None,
        qualification: Optional[str] = None,
        mandal: Optional[str] = None,
        reference: Optional[str] = None,
        account_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves paginated candidate records with filtering and KPI aggregate counts.
        """
        # Base query joined with User
        base_query = (
            select(CandidateProfile, User)
            .join(User, CandidateProfile.user_id == User.id)
            .where(User.role == "CANDIDATE")
        )

        conditions = []

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(CandidateProfile.name).like(term),
                    func.lower(User.email).like(term),
                    func.lower(CandidateProfile.phone).like(term),
                    func.lower(CandidateProfile.mandal).like(term),
                    func.lower(CandidateProfile.village).like(term),
                    func.lower(CandidateProfile.placed_company).like(term),
                    func.lower(CandidateProfile.reference_admin).like(term),
                )
            )

        if placement_status and placement_status.strip().upper() != "ALL":
            p_stat = placement_status.strip().upper()
            if p_stat in ["PLACED", "HIRED"]:
                conditions.append(
                    or_(
                        CandidateProfile.placement_status == "PLACED",
                        and_(
                            CandidateProfile.placed_company.isnot(None),
                            CandidateProfile.placed_company != "",
                        ),
                    )
                )
            elif p_stat in ["NOT_PLACED", "SEEKING", "SEEKING_EMPLOYMENT"]:
                conditions.append(
                    and_(
                        or_(
                            CandidateProfile.placement_status == "NOT_PLACED",
                            CandidateProfile.placement_status.is_(None),
                        ),
                        or_(
                            CandidateProfile.placed_company.is_(None),
                            CandidateProfile.placed_company == "",
                        ),
                    )
                )

        if qualification and qualification.strip().upper() != "ALL":
            q_norm = qualification.strip().upper()
            if q_norm == "10TH":
                conditions.append(func.upper(CandidateProfile.qualification_level) == "10TH")
            elif q_norm == "INTER":
                conditions.append(func.upper(CandidateProfile.qualification_level) == "INTER")
            elif q_norm in ["UG_PG", "GRADUATE"]:
                conditions.append(func.upper(CandidateProfile.qualification_level).in_(["UG", "PG", "UG_PG"]))
            else:
                conditions.append(func.upper(CandidateProfile.qualification_level) == q_norm)

        if mandal and mandal.strip().upper() != "ALL":
            conditions.append(func.lower(CandidateProfile.mandal) == mandal.strip().lower())

        if reference and reference.strip().upper() != "ALL":
            conditions.append(func.lower(CandidateProfile.reference_admin) == reference.strip().lower())

        if account_status and account_status.strip().upper() != "ALL":
            is_active_flag = account_status.strip().upper() == "ACTIVE"
            conditions.append(User.is_active == is_active_flag)

        filtered_query = base_query
        if conditions:
            filtered_query = filtered_query.where(and_(*conditions))

        # Count filtered total
        count_stmt = select(func.count()).select_from(filtered_query.subquery())
        total_filtered = (await db.execute(count_stmt)).scalar() or 0

        # Pagination & Sorting
        offset = (page - 1) * page_size
        results_stmt = (
            filtered_query
            .order_by(CandidateProfile.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(results_stmt)
        rows = res.all()

        # Global Platform KPI calculations from actual records
        kpi_stmt = select(
            func.count(CandidateProfile.id).label("total_registered"),
            func.sum(
                func.if_(
                    or_(
                        CandidateProfile.placement_status == "PLACED",
                        and_(
                            CandidateProfile.placed_company.isnot(None),
                            CandidateProfile.placed_company != "",
                        ),
                    ),
                    1,
                    0,
                )
            ).label("placed_students"),
            func.sum(
                func.if_(func.upper(CandidateProfile.qualification_level) == "10TH", 1, 0)
            ).label("ssc_count"),
            func.sum(
                func.if_(func.upper(CandidateProfile.qualification_level) == "INTER", 1, 0)
            ).label("inter_count"),
            func.sum(
                func.if_(func.upper(CandidateProfile.qualification_level).in_(["UG", "PG", "UG_PG"]), 1, 0)
            ).label("ug_pg_count"),
        ).select_from(CandidateProfile)

        kpi_res = (await db.execute(kpi_stmt)).one_or_none()
        total_registered = int(kpi_res[0] or 0) if kpi_res else 0
        placed_students = int(kpi_res[1] or 0) if kpi_res else 0
        ssc_count = int(kpi_res[2] or 0) if kpi_res else 0
        inter_count = int(kpi_res[3] or 0) if kpi_res else 0
        ug_pg_count = int(kpi_res[4] or 0) if kpi_res else 0

        items = []
        for cand, user in rows:
            masked = mask_aadhaar(cand.aadhaar_number)
            is_placed = cand.placement_status == "PLACED" or bool(cand.placed_company)
            items.append({
                "id": cand.id,
                "user_id": user.id,
                "name": cand.name,
                "email": user.email,
                "phone": cand.phone or user.phone,
                "gender": cand.gender or "Male",
                "aadhaar_masked": masked,
                "district": cand.district or "NTR District",
                "mandal": cand.mandal,
                "village": cand.village,
                "location": cand.location or f"{cand.village + ', ' if cand.village else ''}{cand.mandal or 'Vijayawada Urban'}, {cand.district or 'NTR District'}",
                "qualification_level": cand.qualification_level,
                "education": (
                    f"{cand.qualification_level} Class"
                    if cand.qualification_level in ["10TH", "INTER"]
                    else (cand.qualification_level or "Pending Profile Completion")
                ),
                "headline": cand.headline or "Registered Candidate",
                "profile_completion": cand.profile_completion or 35,
                "profile_status": "BASIC_REGISTERED" if (cand.profile_completion or 35) < 80 else "COMPLETE",
                "placement_status": "PLACED" if is_placed else "NOT_PLACED",
                "placed_company": cand.placed_company or (cand.headline if is_placed else None),
                "placed_role": cand.placed_role,
                "placed_salary": cand.placed_salary,
                "placed_date": cand.placed_date,
                "reference_admin": cand.reference_admin or "Admin User (State Operations)",
                "custom_referrer": cand.custom_referrer,
                "account_status": "ACTIVE" if user.is_active else "SUSPENDED",
                "registration_date": cand.created_at.strftime("%Y-%m-%d") if cand.created_at else None,
                "created_at": cand.created_at,
                "applications_count": 0,
            })

        return {
            "items": items,
            "total": total_filtered,
            "page": page,
            "page_size": page_size,
            "total_registered": total_registered,
            "placed_students": placed_students,
            "ssc_count": ssc_count,
            "inter_count": inter_count,
            "ug_pg_count": ug_pg_count,
        }

    @staticmethod
    async def create_candidate(
        db: AsyncSession,
        user: User,
        candidate: CandidateProfile,
    ) -> Tuple[User, CandidateProfile]:
        db.add(user)
        db.add(candidate)
        settings = CandidateSettings(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            email_job_application_alerts=True,
            sms_whatsapp_notifications=True,
            upcoming_interview_reminders=True,
            weekly_job_recommendation_digest=False,
            visible_in_recruiter_talent_search=True,
            direct_recruiter_messages=True,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(user)
        await db.refresh(candidate)
        return user, candidate

    @staticmethod
    async def update_candidate_placement(
        db: AsyncSession,
        candidate_id: str,
        placement_status: str,
        placed_company: Optional[str] = None,
        placed_role: Optional[str] = None,
        placed_salary: Optional[str] = None,
        placed_date: Optional[str] = None,
    ) -> Optional[CandidateProfile]:
        stmt = select(CandidateProfile).where(
            or_(
                CandidateProfile.id == candidate_id,
                CandidateProfile.user_id == candidate_id,
            )
        )
        res = await db.execute(stmt)
        cand = res.scalars().first()
        if not cand:
            return None

        is_placed = placement_status.strip().upper() in ["PLACED", "HIRED"]
        cand.placement_status = "PLACED" if is_placed else "NOT_PLACED"
        cand.placed_company = placed_company.strip() if (is_placed and placed_company) else None
        cand.placed_role = placed_role.strip() if (is_placed and placed_role) else None
        cand.placed_salary = placed_salary.strip() if (is_placed and placed_salary) else None
        cand.placed_date = placed_date.strip() if (is_placed and placed_date) else None

        await db.commit()
        await db.refresh(cand)
        return cand

    @staticmethod
    async def update_candidate_status(
        db: AsyncSession,
        candidate_id: str,
        is_active: bool,
    ) -> Optional[Tuple[CandidateProfile, User]]:
        stmt = (
            select(CandidateProfile, User)
            .join(User, CandidateProfile.user_id == User.id)
            .where(
                or_(
                    CandidateProfile.id == candidate_id,
                    CandidateProfile.user_id == candidate_id,
                )
            )
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            return None

        cand, user = row
        user.is_active = is_active
        await db.commit()
        await db.refresh(user)
        await db.refresh(cand)
        return cand, user
