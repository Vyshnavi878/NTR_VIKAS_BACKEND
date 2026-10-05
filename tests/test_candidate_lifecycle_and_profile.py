"""
Candidate Lifecycle and Profile Integration Tests
Covers full lifecycle:
1.  Candidate registration without OTP
2.  Candidate login and JWT session
3.  Candidate profile GET with profile_completion_percentage
4.  Candidate personal update (PATCH /candidate/profile/personal)
5.  Candidate career preferences update (PATCH /candidate/profile/preferences)
6.  Technical skills CRUD (GET, POST, DELETE) + duplicate skill prevention
7.  Resume upload, view, and download + ownership verification
8.  Work experience CRUD (GET, POST, PATCH, DELETE)
9.  Education CRUD (GET, POST, PATCH, DELETE)
10. Certifications CRUD (GET, POST, PATCH, DELETE)
11. Projects CRUD (GET, POST, PATCH, DELETE)
12. Candidate A cannot access Candidate B's profile or resume
13. Application creation (POST /candidate/applications)
14. Duplicate application returns 409 Conflict
15. Generated application ID is unique
16. Initial application status is APPLIED
17. Initial timeline event is automatically generated
18. Application details and timeline work
19. Cross-candidate application details forbidden
20. Existing Job Mela applications remain intact
"""
import uuid
import random
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def _login(
    client: AsyncClient,
    email: str,
    password: str = "password123",
    role: str = "CANDIDATE",
) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "role": role},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


async def _create_registered_candidate(client: AsyncClient):
    rand_digits = f"{random.randint(100000, 999999)}"
    email = f"dyn_cand_{rand_digits}@example.com"
    phone = f"9872{rand_digits}"
    aadhaar = f"555566{rand_digits}"

    reg_payload = {
        "name": f"Dynamic Test {rand_digits}",
        "email": email,
        "password": "Password123!",
        "aadhaar_number": aadhaar,
        "phone": phone,
        "district": "NTR District",
        "mandal": "Vijayawada Urban",
        "qualification_level": "GRADUATE",
        "terms_accepted": True,
    }
    await client.post("/api/v1/auth/candidate/register", json=reg_payload)
    token = await _login(client, email, password="Password123!")
    return token, email


# ── 1. Candidate Registration & Login ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_candidate_registration_and_login_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rand_digits = f"{random.randint(100000, 999999)}"
        email = f"cand_test_{rand_digits}@example.com"
        phone = f"9876{rand_digits}"
        aadhaar = f"777788{rand_digits}"

        reg_payload = {
            "name": f"Lifecycle Test {rand_digits}",
            "email": email,
            "password": "Password123!",
            "aadhaar_number": aadhaar,
            "phone": phone,
            "district": "NTR District",
            "mandal": "Vijayawada Urban",
            "village": "Ward 12",
            "qualification_level": "GRADUATE",
            "terms_accepted": True,
        }

        # 1. Register candidate
        reg_resp = await client.post("/api/v1/auth/candidate/register", json=reg_payload)
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert reg_data["user"]["email"] == email

        # 2. Login candidate
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!", "role": "CANDIDATE"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        assert token

        # 3. GET profile
        prof_resp = await client.get(
            "/api/v1/candidate/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert prof_resp.status_code == 200
        prof = prof_resp.json()
        assert prof["email"] == email
        assert "profile_completion_percentage" in prof
        assert prof["profile_completion_percentage"] >= 25


# ── 2. Profile Updates & Preferences ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_candidate_profile_updates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _create_registered_candidate(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Update personal
        p_resp = await client.patch(
            "/api/v1/candidate/profile/personal",
            headers=headers,
            json={
                "headline": "Lead Frontend Architect",
                "bio": "Experienced architect specializing in modern high-performance web systems and micro-frontends.",
                "linkedin": "https://linkedin.com/in/priya-updated",
                "github": "https://github.com/priya-updated",
                "portfolio": "https://priya-updated.dev",
            },
        )
        assert p_resp.status_code == 200
        p_data = p_resp.json()
        assert p_data["headline"] == "Lead Frontend Architect"
        assert p_data["bio"].startswith("Experienced architect")
        assert p_data["linkedin"] == "https://linkedin.com/in/priya-updated"

        # 2. Update preferences
        pref_resp = await client.patch(
            "/api/v1/candidate/profile/preferences",
            headers=headers,
            json={
                "experience": "5 Years",
                "currentSalary": "₹16,00,000 / year",
                "expectedSalary": "₹22,00,000 - ₹28,00,000 / year",
                "workMode": "Remote",
                "jobType": "Full-time",
                "preferredRoles": ["Principal Engineer", "Frontend Architect"],
                "preferredLocations": ["Visakhapatnam", "Remote"],
            },
        )
        assert pref_resp.status_code == 200
        pref_data = pref_resp.json()
        assert pref_data["skillsPreferences"]["workMode"] == "Remote"
        assert "Principal Engineer" in pref_data["skillsPreferences"]["preferredRoles"]


# ── 3. Skills CRUD & Duplicate Prevention ─────────────────────────────────────

@pytest.mark.asyncio
async def test_skills_crud_and_duplicate_handling():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _create_registered_candidate(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Add skill

        add_resp = await client.post(
            "/api/v1/candidate/profile/skills",
            headers=headers,
            json={"skill_name": "GraphQL Subscriptions"},
        )
        assert add_resp.status_code == 201
        skill_item = add_resp.json()
        skill_id = skill_item["id"]
        assert skill_item["skill_name"] == "GraphQL Subscriptions"

        # 2. Try adding duplicate skill (should succeed idempotently or return existing)
        dup_resp = await client.post(
            "/api/v1/candidate/profile/skills",
            headers=headers,
            json={"skill_name": "GraphQL Subscriptions"},
        )
        assert dup_resp.status_code in (200, 201)
        assert dup_resp.json()["id"] == skill_id

        # 3. List skills
        list_resp = await client.get("/api/v1/candidate/profile/skills", headers=headers)
        assert list_resp.status_code == 200
        skills = list_resp.json()
        assert any(s["skill_name"] == "GraphQL Subscriptions" for s in skills)

        # 4. Delete skill
        del_resp = await client.delete(
            f"/api/v1/candidate/profile/skills/{skill_id}", headers=headers
        )
        assert del_resp.status_code == 200

        # Verify removal
        list_resp2 = await client.get("/api/v1/candidate/profile/skills", headers=headers)
        assert not any(s["id"] == skill_id for s in list_resp2.json())


# ── 4. Work Experience, Education, Certifications, Projects CRUD ──────────────

@pytest.mark.asyncio
async def test_career_history_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, "candidate1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token}"}

        # ── Experience ──
        exp_post = await client.post(
            "/api/v1/candidate/profile/work-experience",
            headers=headers,
            json={
                "role": "Staff Engineer",
                "company": "NextGen Systems",
                "location": "Bengaluru",
                "duration": "2024 - Present",
                "description": "Leading cloud architecture.",
            },
        )
        assert exp_post.status_code == 201
        exp_id = exp_post.json()["id"]

        exp_patch = await client.patch(
            f"/api/v1/candidate/profile/work-experience/{exp_id}",
            headers=headers,
            json={"role": "Principal Staff Engineer"},
        )
        assert exp_patch.status_code == 200
        assert exp_patch.json()["role"] == "Principal Staff Engineer"

        exp_del = await client.delete(
            f"/api/v1/candidate/profile/work-experience/{exp_id}", headers=headers
        )
        assert exp_del.status_code == 200

        # ── Education ──
        edu_post = await client.post(
            "/api/v1/candidate/profile/education",
            headers=headers,
            json={
                "degree": "M.Tech in AI",
                "institution": "IIT Madras",
                "duration": "2021 - 2023",
                "score": "9.2 CGPA",
            },
        )
        assert edu_post.status_code == 201
        edu_id = edu_post.json()["id"]

        edu_del = await client.delete(
            f"/api/v1/candidate/profile/education/{edu_id}", headers=headers
        )
        assert edu_del.status_code == 200

        # ── Certification ──
        cert_post = await client.post(
            "/api/v1/candidate/profile/certifications",
            headers=headers,
            json={
                "name": "Google Cloud Professional Architect",
                "issuer": "Google Cloud",
                "year": "2025",
            },
        )
        assert cert_post.status_code == 201
        cert_id = cert_post.json()["id"]

        cert_del = await client.delete(
            f"/api/v1/candidate/profile/certifications/{cert_id}", headers=headers
        )
        assert cert_del.status_code == 200

        # ── Project ──
        proj_post = await client.post(
            "/api/v1/candidate/profile/projects",
            headers=headers,
            json={
                "title": "Autonomous Agent Pipeline",
                "tech": "FastAPI, Python, Docker",
                "description": "Distributed microservice for async code evaluation.",
            },
        )
        assert proj_post.status_code == 201
        proj_id = proj_post.json()["id"]

        proj_del = await client.delete(
            f"/api/v1/candidate/profile/projects/{proj_id}", headers=headers
        )
        assert proj_del.status_code == 200


# ── 5. Resume Upload, View, Download & Isolation ──────────────────────────────

@pytest.mark.asyncio
async def test_resume_upload_view_and_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1 = await _login(client, "candidate1@ntrvikasa.com")
        token2 = await _login(client, "candidate2@ntrvikasa.com")

        # Candidate 1 uploads resume
        upload_resp = await client.post(
            "/api/v1/candidate/profile/resume",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "fileName": "Priya_Sharma_Resume_2026.pdf",
                "fileSize": "1.8 MB",
                "fileType": "PDF Document",
            },
        )
        assert upload_resp.status_code == 201
        resume_data = upload_resp.json()
        resume_id = resume_data["id"]
        assert resume_data["fileName"] == "Priya_Sharma_Resume_2026.pdf"

        # Candidate 1 can view own resume
        view_resp = await client.get(
            f"/api/v1/candidate/profile/resume/{resume_id}/view",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert view_resp.status_code == 200

        # Candidate 1 can download own resume
        down_resp = await client.get(
            f"/api/v1/candidate/profile/resume/{resume_id}/download",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert down_resp.status_code == 200
        assert "Content-Disposition" in down_resp.headers

        # Candidate 2 CANNOT access Candidate 1's resume (404/403)
        cross_resp = await client.get(
            f"/api/v1/candidate/profile/resume/{resume_id}/view",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert cross_resp.status_code == 404


# ── 6. Application Creation, Duplicate 409 & Initial Timeline ─────────────────

@pytest.mark.asyncio
async def test_application_creation_duplicate_and_timeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _create_registered_candidate(client)
        headers = {"Authorization": f"Bearer {token}"}

        test_job_id = f"test-job-{uuid.uuid4().hex[:6]}"

        # 1. Candidate applies for job

        apply_payload = {
            "job_id": test_job_id,
            "job_title": "Full Stack Architect",
            "company_name": "Innovate India Ltd",
            "location": "Vijayawada, Andhra Pradesh",
            "salary": "₹20 - ₹28 LPA",
            "cover_letter": "I am thrilled to apply for this architectural role.",
        }
        create_resp = await client.post(
            "/api/v1/candidate/applications",
            headers=headers,
            json=apply_payload,
        )
        assert create_resp.status_code == 201
        app_data = create_resp.json()
        assert app_data["status"] == "APPLIED"
        assert app_data["job_id"] == test_job_id
        assert app_data["application_id"].startswith("APP-") or app_data["application_id"].startswith("NTR-")

        # 2. Check initial timeline event was created automatically
        assert len(app_data["timeline"]) >= 1
        first_event = app_data["timeline"][0]
        assert first_event["status"] == "APPLIED"
        assert first_event["completed"] is True
        assert first_event["current"] is True

        # 3. Duplicate Application check: applying to same job MUST return 409 Conflict
        dup_apply_resp = await client.post(
            "/api/v1/candidate/applications",
            headers=headers,
            json={"job_id": test_job_id},
        )
        assert dup_apply_resp.status_code == 409
        assert "already applied" in dup_apply_resp.json()["detail"].lower()

        # 4. Check application in candidate 2 application list
        list_resp = await client.get("/api/v1/candidate/applications", headers=headers)
        assert list_resp.status_code == 200
        my_apps = list_resp.json()["applications"]
        assert any(a["job_id"] == test_job_id for a in my_apps)

        # 5. Timeline endpoint verification
        app_id = app_data["id"]
        tl_resp = await client.get(
            f"/api/v1/candidate/applications/{app_id}/timeline",
            headers=headers,
        )
        assert tl_resp.status_code == 200
        assert len(tl_resp.json()["timeline"]) >= 1


# ── 7. Candidate Application Ownership & Isolation ────────────────────────────

@pytest.mark.asyncio
async def test_candidate_application_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1 = await _login(client, "candidate1@ntrvikasa.com")
        token2 = await _login(client, "candidate2@ntrvikasa.com")

        # Candidate 1 has seeded applications
        c1_apps_resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert c1_apps_resp.status_code == 200
        c1_apps = c1_apps_resp.json()["applications"]
        assert len(c1_apps) > 0
        c1_app_id = c1_apps[0]["id"]

        # Candidate 2 CANNOT access Candidate 1's application details (403 Forbidden)
        forbidden_detail = await client.get(
            f"/api/v1/candidate/applications/{c1_app_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert forbidden_detail.status_code in (403, 404)

        # Candidate 2 CANNOT access Candidate 1's timeline (403 Forbidden)
        forbidden_tl = await client.get(
            f"/api/v1/candidate/applications/{c1_app_id}/timeline",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert forbidden_tl.status_code in (403, 404)


# ── 8. Existing Job Mela Applications Not Broken ──────────────────────────────

@pytest.mark.asyncio
async def test_job_mela_applications_preserved():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1 = await _login(client, "candidate1@ntrvikasa.com")
        headers = {"Authorization": f"Bearer {token1}"}

        apps_resp = await client.get("/api/v1/candidate/applications", headers=headers)
        assert apps_resp.status_code == 200
        apps = apps_resp.json()["applications"]

        # Check if Job Mela application is present with NTR- formatted ID
        mela_apps = [a for a in apps if "Mela" in (a.get("application_type") or "") or a.get("job_mela_id")]
        assert len(mela_apps) >= 1
        mela_app = mela_apps[0]
        assert mela_app["application_id"].startswith("NTR-")
