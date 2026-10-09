import asyncio
import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.database.session import AsyncSessionLocal
from app.models.recruiter import RecruiterProfile
from app.models.user import User
from app.models.company_team import CompanyMember
from app.core.security import hash_password


COMPANIES_DATA = [
    {
        "company_name": "Tech Solutions Global Ltd",
        "recruiter_name": "Sneha Rao",
        "email": "sneha.rao@techsolutionsglobal.com",
        "phone": "+91 91234 88776",
        "designation": "Head of People & University Talent",
        "industry": "Banking & Financial Services",
        "location": "MG Road, Vijayawada Urban, NTR District",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "status": "APPROVED",
        "user_is_active": True,
    },
    {
        "company_name": "Fintech Corp India Pvt Ltd",
        "recruiter_name": "Rahul Mehta",
        "email": "rahul.mehta@fintechcorp.example.com",
        "phone": "+91 98111 22334",
        "designation": "Lead Technical Recruiter",
        "industry": "Banking & Financial Services",
        "location": "Benz Circle, Vijayawada Urban, NTR District",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "status": "PENDING_APPROVAL",
        "user_is_active": True,
    },
    {
        "company_name": "HealthPlus Systems Ltd",
        "recruiter_name": "Divya Iyer",
        "email": "divya.iyer@healthplus.example.com",
        "phone": "+91 98222 33445",
        "designation": "Senior HR Talent Manager",
        "industry": "Healthcare & Pharmaceuticals",
        "location": "Governerpet, Vijayawada Urban, NTR District",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "status": "PENDING_APPROVAL",
        "user_is_active": True,
    },
    {
        "company_name": "Fast Cash Enterprises",
        "recruiter_name": "Manoj Kumar",
        "email": "manoj.k@fastcashenterprises.com",
        "phone": "+91 99999 00000",
        "designation": "Hiring Agent",
        "industry": "Retail & E-Commerce",
        "location": "One Town, Vijayawada Urban, NTR District",
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "status": "SUSPENDED",
        "user_is_active": False,
        "rejection_reason": "Invalid CIN registration and fraudulent fee collection attempt.",
    },
    {
        "company_name": "NextGen Autonomous Robotics",
        "recruiter_name": "Vikram Sarabhai",
        "email": "vikram@nextgenrobotics.example.com",
        "phone": "+91 98333 44556",
        "designation": "Staff Talent Partner",
        "industry": "Manufacturing & Automobile",
        "location": "Kondapalli Industrial Estate, Ibrahimpatnam",
        "district": "NTR District",
        "mandal": "Ibrahimpatnam",
        "status": "APPROVED",
        "user_is_active": True,
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        created_count = 0

        for item in COMPANIES_DATA:
            # Check if company or recruiter exists
            stmt = select(RecruiterProfile).where(
                func.lower(RecruiterProfile.company_name) == item["company_name"].lower()
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                print(f"Company already exists: {item['company_name']}")
                continue

            # Check if user exists
            u_stmt = select(User).where(User.email == item["email"].lower())
            user = (await db.execute(u_stmt)).scalar_one_or_none()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    email=item["email"].lower(),
                    phone=item["phone"],
                    hashed_password=hash_password("Password@123"),
                    role="RECRUITER",
                    is_active=item["user_is_active"],
                    is_verified=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(user)
                await db.flush()

            profile = RecruiterProfile(
                id=str(uuid.uuid4()),
                user_id=user.id,
                recruiter_name=item["recruiter_name"],
                designation=item["designation"],
                work_email=item["email"].lower(),
                mobile_phone=item["phone"],
                company_name=item["company_name"],
                company_website=f"https://www.{item['company_name'].lower().replace(' ', '')}.com",
                corporate_email=item["email"].lower(),
                company_phone=item["phone"],
                primary_industry=item["industry"],
                company_size="100-500 employees",
                headquarters_city_state=item["location"],
                registered_office_address=item["location"],
                company_description=f"{item['company_name']} is a verified partner operating in {item['industry']}.",
                district=item["district"],
                mandal=item["mandal"],
                village="",
                status=item["status"],
                rejection_reason=item.get("rejection_reason"),
                onboarded_by_admin_id="admin-1",
                onboarded_by_role="ADMIN",
                reviewed_by="admin1@ntrvikasa.com" if item["status"] != "PENDING_APPROVAL" else None,
                reviewed_at=now if item["status"] != "PENDING_APPROVAL" else None,
                created_at=now,
                updated_at=now,
            )
            db.add(profile)
            await db.flush()

            # Member link
            member = CompanyMember(
                id=str(uuid.uuid4()),
                company_id=profile.id,
                user_id=user.id,
                role=item["designation"],
                status="ACTIVE" if item["user_is_active"] else "SUSPENDED",
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(member)
            created_count += 1
            print(f"Created recruiter & company: {item['recruiter_name']} ({item['company_name']}) - Status: {item['status']}")

        await db.commit()
        print(f"Done! Seeded {created_count} recruiters and companies.")


if __name__ == "__main__":
    asyncio.run(seed())
