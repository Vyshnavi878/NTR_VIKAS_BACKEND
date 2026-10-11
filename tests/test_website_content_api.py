import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


async def get_admin_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "admin1@ntrvikasa.com", "password": "password123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def get_candidate_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": "candidate1@ntrvikasa.com", "password": "password123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_list_and_filter_gallery_photos():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Retrieve list
        res = await client.get("/api/v1/admin/website-content/gallery/photos", headers=headers)
        assert res.status_code == 200
        photos = res.json()
        assert isinstance(photos, list)
        assert len(photos) >= 6

        # Check required fields
        p0 = photos[0]
        assert "id" in p0
        assert "title" in p0
        assert "category" in p0
        assert "image_url" in p0
        assert "imageUrl" in p0
        assert "is_published" in p0

        # 2. Filter by category
        res_cat = await client.get("/api/v1/admin/website-content/gallery/photos?category=Job Melas", headers=headers)
        assert res_cat.status_code == 200
        for p in res_cat.json():
            assert p["category"] == "Job Melas"

        # 3. Search by keyword
        res_search = await client.get("/api/v1/admin/website-content/gallery/photos?search=Vijayawada", headers=headers)
        assert res_search.status_code == 200
        assert len(res_search.json()) >= 1


@pytest.mark.asyncio
async def test_admin_photo_crud_lifecycle_and_public_sync():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin creates a new photo
        new_photo_payload = {
            "title": "NTR District Youth Career Summit 2026",
            "category": "Youth Summits",
            "date": "24 Oct 2026",
            "image_url": "https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=800",
            "description": "Interactive career conclave and placement symposium.",
            "display_order": 0,
            "is_published": True,
        }
        res_create = await client.post(
            "/api/v1/admin/website-content/gallery/photos",
            json=new_photo_payload,
            headers=admin_headers,
        )
        assert res_create.status_code == 201
        created_photo = res_create.json()
        photo_id = created_photo["id"]
        assert created_photo["title"] == new_photo_payload["title"]
        assert created_photo["category"] == "Youth Summits"

        # 2. Verify Home / Public page sees the EXACT same photo record
        res_public = await client.get("/api/v1/public/website-content/gallery/photos")
        assert res_public.status_code == 200
        public_photos = res_public.json()
        matching_pub = next((p for p in public_photos if p["id"] == photo_id), None)
        assert matching_pub is not None, "New photo must appear in public gallery endpoints from the same DB record"
        assert matching_pub["title"] == new_photo_payload["title"]

        # 3. Admin edits photo
        update_payload = {
            "title": "NTR District Youth Career Summit 2026 (Updated Edition)",
            "description": "Updated description with keynote speaker details.",
        }
        res_patch = await client.patch(
            f"/api/v1/admin/website-content/gallery/photos/{photo_id}",
            json=update_payload,
            headers=admin_headers,
        )
        assert res_patch.status_code == 200
        patched = res_patch.json()
        assert patched["id"] == photo_id
        assert patched["title"] == update_payload["title"]

        # Public page immediately reflects the edited title
        res_pub_updated = await client.get("/api/v1/public/website-content/gallery/photos")
        assert res_pub_updated.status_code == 200
        matching_pub_updated = next((p for p in res_pub_updated.json() if p["id"] == photo_id), None)
        assert matching_pub_updated is not None
        assert matching_pub_updated["title"] == update_payload["title"]

        # 4. Unpublish photo -> Must vanish from public endpoints
        res_unpub = await client.patch(
            f"/api/v1/admin/website-content/gallery/photos/{photo_id}",
            json={"is_published": False},
            headers=admin_headers,
        )
        assert res_unpub.status_code == 200

        res_pub_after_unpub = await client.get("/api/v1/public/website-content/gallery/photos")
        assert not any(p["id"] == photo_id for p in res_pub_after_unpub.json()), "Unpublished photo must not appear in public results"

        # 5. Delete photo
        res_del = await client.delete(f"/api/v1/admin/website-content/gallery/photos/{photo_id}", headers=admin_headers)
        assert res_del.status_code == 204

        # Verify 404 on get
        res_get_del = await client.get(f"/api/v1/admin/website-content/gallery/photos/{photo_id}", headers=admin_headers)
        assert res_get_del.status_code == 404


@pytest.mark.asyncio
async def test_admin_video_gallery_crud_and_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Invalid / Malicious YouTube URL rejection
        res_bad = await client.post(
            "/api/v1/admin/website-content/gallery/videos",
            json={
                "title": "Malicious Video",
                "youtube_url": "<script>alert('xss')</script>",
                "category": "General",
            },
            headers=admin_headers,
        )
        assert res_bad.status_code == 422

        # 2. Valid video creation
        res_create = await client.post(
            "/api/v1/admin/website-content/gallery/videos",
            json={
                "title": "State Innovation & Apprenticeship Expo 2026",
                "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                "category": "Conferences",
                "date": "10 Oct 2026",
                "description": "Video coverage of corporate technology exhibits.",
            },
            headers=admin_headers,
        )
        assert res_create.status_code == 201
        video = res_create.json()
        vid_id = video["id"]
        assert "youtube.com/watch?v=dQw4w9WgXcQ" in video["youtube_url"]

        # 3. Public video endpoint returns the video
        res_pub_v = await client.get("/api/v1/public/website-content/gallery/videos")
        assert res_pub_v.status_code == 200
        assert any(v["id"] == vid_id for v in res_pub_v.json())

        # 4. Clean up
        res_del = await client.delete(f"/api/v1/admin/website-content/gallery/videos/{vid_id}", headers=admin_headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_admin_press_articles_crud_and_public_sync():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. List press articles
        res_list = await client.get("/api/v1/admin/website-content/press", headers=admin_headers)
        assert res_list.status_code == 200
        articles = res_list.json()
        assert isinstance(articles, list)
        assert len(articles) >= 4

        # 2. Create new press clipping
        new_press = {
            "newspaper": "Andhra Jyothi",
            "title": "ఎన్టీఆర్ జిల్లాలో 1200 మందికి ఉద్యోగ ఆఫర్లు",
            "date": "20 Oct 2026",
            "edition": "Vijayawada City Main Edition",
            "image_url": "/news/news-sakshi-job-mela.png",
            "source_url": "https://www.andhrajyothy.com/",
            "summary": "విజయవాడలో నిర్వహించిన మెగా జాబ్ మేళా ద్వారా ప్రముఖ సంస్థలలో రికార్డు నియామకాలు.",
            "category": "Press Coverage",
            "display_order": 0,
            "is_published": True,
        }
        res_create = await client.post("/api/v1/admin/website-content/press", json=new_press, headers=admin_headers)
        assert res_create.status_code == 201
        created_press = res_create.json()
        press_id = created_press["id"]
        assert created_press["newspaper"] == "Andhra Jyothi"
        assert created_press["title"] == new_press["title"]

        # 3. Public press endpoint returns the clipping
        res_pub_p = await client.get("/api/v1/public/website-content/press")
        assert res_pub_p.status_code == 200
        assert any(p["id"] == press_id for p in res_pub_p.json())

        # 4. Edit press clipping
        res_patch = await client.patch(
            f"/api/v1/admin/website-content/press/{press_id}",
            json={"edition": "Vijayawada City Main Edition — Special Report"},
            headers=admin_headers,
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["edition"] == "Vijayawada City Main Edition — Special Report"

        # 5. Delete press clipping
        res_del = await client.delete(f"/api/v1/admin/website-content/press/{press_id}", headers=admin_headers)
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_website_content_security_and_unauthorized_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        candidate_token = await get_candidate_token(client)
        cand_headers = {"Authorization": f"Bearer {candidate_token}"}

        # 1. Unauthenticated request to admin endpoints -> 401
        res_unauth = await client.post(
            "/api/v1/admin/website-content/gallery/photos",
            json={"title": "Hacker Photo", "image_url": "https://bad.com/img.jpg"},
        )
        assert res_unauth.status_code in (401, 403)

        # 2. Candidate role attempting admin operations -> 403 Forbidden
        res_cand = await client.post(
            "/api/v1/admin/website-content/gallery/photos",
            json={"title": "Unauthorized Photo", "image_url": "https://test.com/img.jpg"},
            headers=cand_headers,
        )
        assert res_cand.status_code == 403

        # 3. Candidate role attempting to delete press -> 403 Forbidden
        res_cand_del = await client.delete(
            "/api/v1/admin/website-content/press/news-1",
            headers=cand_headers,
        )
        assert res_cand_del.status_code == 403


@pytest.mark.asyncio
async def test_website_section_header_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Update gallery header
        res_put = await client.put(
            "/api/v1/admin/website-content/sections/gallery",
            json={
                "badge": "State Highlights",
                "heading1": "NTR VIKASA Official",
                "heading2": "Media Gallery 2026",
                "subtitle": "Updated subtitle for the public portal.",
            },
            headers=admin_headers,
        )
        assert res_put.status_code == 200
        hdr = res_put.json()
        assert hdr["badge"] == "State Highlights"
        assert hdr["heading1"] == "NTR VIKASA Official"

        # Public retrieval
        res_pub_hdr = await client.get("/api/v1/public/website-content/sections/gallery")
        assert res_pub_hdr.status_code == 200
        assert res_pub_hdr.json()["heading1"] == "NTR VIKASA Official"


@pytest.mark.asyncio
async def test_news_press_endpoint_aliases_and_header_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Test /admin/website-content/news-press list alias
        res_list = await client.get("/api/v1/admin/website-content/news-press", headers=admin_headers)
        assert res_list.status_code == 200
        assert isinstance(res_list.json(), list)

        # 2. Test create via /admin/website-content/news-press
        new_clipping = {
            "newspaper": "Eenadu",
            "title": "నూతన వికాస కార్యక్రమాలు - ఉద్యోగ విప్లవం",
            "date": "22 Oct 2026",
            "edition": "Amaravati State Bureau",
            "image_url": "/news/news-eenadu-job-mela.png",
            "source_url": "https://epaper.eenadu.net/",
            "summary": "రాష్ట్రవ్యాప్తంగా యువతకు ఉపాధి అవకాశాల కల్పనపై ప్రత్యేక కథనం.",
            "category": "Press Coverage",
            "is_published": True,
        }
        res_create = await client.post(
            "/api/v1/admin/website-content/news-press",
            json=new_clipping,
            headers=admin_headers,
        )
        assert res_create.status_code == 201
        created_id = res_create.json()["id"]

        # 3. Test direct public endpoint /public/news-press and /public/website-content/news-press
        res_pub1 = await client.get("/api/v1/public/news-press")
        assert res_pub1.status_code == 200
        assert any(p["id"] == created_id for p in res_pub1.json())

        res_pub2 = await client.get("/api/v1/public/website-content/news-press")
        assert res_pub2.status_code == 200
        assert any(p["id"] == created_id for p in res_pub2.json())

        # 4. Test header settings GET and PATCH via /news-press/settings
        settings_payload = {
            "badge": "Media & News Bulletin",
            "heading1": "Official Press &",
            "heading2": "Authentic Coverage",
            "subtitle": "Updated coverage description for the portal.",
        }
        res_patch_hdr = await client.patch(
            "/api/v1/admin/website-content/news-press/settings",
            json=settings_payload,
            headers=admin_headers,
        )
        assert res_patch_hdr.status_code == 200
        assert res_patch_hdr.json()["heading1"] == "Official Press &"

        res_get_hdr = await client.get(
            "/api/v1/admin/website-content/news-press/settings",
            headers=admin_headers,
        )
        assert res_get_hdr.status_code == 200
        assert res_get_hdr.json()["badge"] == "Media & News Bulletin"

        res_pub_news_hdr = await client.get("/api/v1/public/website-content/news-press/settings")
        assert res_pub_news_hdr.status_code == 200
        assert res_pub_news_hdr.json()["heading2"] == "Authentic Coverage"

        # 5. Clean up created clipping
        res_del = await client.delete(
            f"/api/v1/admin/website-content/news-press/{created_id}",
            headers=admin_headers,
        )
        assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_admin_and_public_jobs_page_content_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin gets current configuration
        res_admin = await client.get("/api/v1/admin/website-content/jobs-page", headers=admin_headers)
        assert res_admin.status_code == 200
        config = res_admin.json()
        assert "hero" in config
        assert "search" in config
        assert "locations" in config
        assert len(config["locations"]) == 36

        # 2. Admin updates Hero
        new_hero = {
            "badge": "Top Notch Careers 2026",
            "heading": "Launch Your Dream Career Across AP",
            "subtitle": "Discover over 3,000+ verified corporate job listings.",
        }
        res_hero = await client.patch(
            "/api/v1/admin/website-content/jobs-page/hero",
            json=new_hero,
            headers=admin_headers,
        )
        assert res_hero.status_code == 200
        assert res_hero.json()["hero"]["badge"] == new_hero["badge"]
        assert res_hero.json()["hero"]["heading"] == new_hero["heading"]

        # 3. Public Jobs page immediately reflects new hero
        res_pub = await client.get("/api/v1/public/website-content/jobs-page")
        assert res_pub.status_code == 200
        pub_config = res_pub.json()
        assert pub_config["hero"]["badge"] == new_hero["badge"]
        assert pub_config["hero"]["heading"] == new_hero["heading"]
        assert pub_config["hero"]["subtitle"] == new_hero["subtitle"]

        # 4. Admin updates search placeholders
        new_search = {
            "searchPlaceholder": "Search by role (e.g. Java, AWS, React) or company...",
            "locationPlaceholder": "Select State or UT (All India)",
        }
        res_search = await client.patch(
            "/api/v1/admin/website-content/jobs-page/search",
            json=new_search,
            headers=admin_headers,
        )
        assert res_search.status_code == 200
        assert res_search.json()["search"]["searchPlaceholder"] == new_search["searchPlaceholder"]
        assert res_search.json()["search"]["locationPlaceholder"] == new_search["locationPlaceholder"]

        # 5. Public Jobs page reflects search placeholders
        res_pub2 = await client.get("/api/v1/public/website-content/jobs-page")
        assert res_pub2.status_code == 200
        assert res_pub2.json()["search"]["searchPlaceholder"] == new_search["searchPlaceholder"]
        assert res_pub2.json()["search"]["locationPlaceholder"] == new_search["locationPlaceholder"]

        # 6. Admin resets Jobs page defaults
        res_reset = await client.post("/api/v1/admin/website-content/jobs-page/reset", headers=admin_headers)
        assert res_reset.status_code == 200
        reset_cfg = res_reset.json()
        assert reset_cfg["hero"]["badge"] == "Corporate Recruitment Portal"
        assert reset_cfg["search"]["locationPlaceholder"] == "All Locations (All India)"


@pytest.mark.asyncio
async def test_popular_searches_validation_and_deduplication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Send list with leading/trailing spaces, empty string, and case-insensitive duplicates
        keywords_payload = {
            "popularSearches": [
                "  Python Developer  ",
                "React JS",
                "python developer",  # duplicate, different case
                "   ",  # empty after trim
                "Data Analyst",
                "REACT JS",  # duplicate, upper case
                "Cloud Engineer",
            ]
        }
        res = await client.patch(
            "/api/v1/admin/website-content/jobs-page/popular-searches",
            json=keywords_payload,
            headers=admin_headers,
        )
        assert res.status_code == 200
        saved_popular = res.json()["search"]["popularSearches"]
        # Must have trimmed, rejected empty, deduped case-insensitively, and preserved first casing
        assert saved_popular == ["Python Developer", "React JS", "Data Analyst", "Cloud Engineer"]

        # Verify on public endpoint
        res_pub = await client.get("/api/v1/public/website-content/jobs-page")
        assert res_pub.status_code == 200
        assert res_pub.json()["search"]["popularSearches"] == ["Python Developer", "React JS", "Data Analyst", "Cloud Engineer"]


@pytest.mark.asyncio
async def test_job_locations_active_filter_and_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin gets all 36 regions
        res_admin_locs = await client.get("/api/v1/admin/website-content/jobs-page/locations", headers=admin_headers)
        assert res_admin_locs.status_code == 200
        admin_locs = res_admin_locs.json()
        assert len(admin_locs) == 36

        # 2. Public gets all 36 active regions
        res_pub_locs = await client.get("/api/v1/public/job-locations")
        assert res_pub_locs.status_code == 200
        pub_locs = res_pub_locs.json()
        assert len(pub_locs["states"]) == 28
        assert len(pub_locs["union_territories"]) == 8
        assert "Goa" in pub_locs["states"]

        # Find Goa ID
        goa = next((l for l in admin_locs if l["name"] == "Goa"), None)
        assert goa is not None

        # 3. Deactivate Goa
        res_deact = await client.patch(
            f"/api/v1/admin/website-content/jobs-page/locations/{goa['id']}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert res_deact.status_code == 200
        assert res_deact.json()["is_active"] is False

        # 4. Public endpoint now excludes Goa
        res_pub_locs_after = await client.get("/api/v1/public/job-locations")
        assert res_pub_locs_after.status_code == 200
        assert "Goa" not in res_pub_locs_after.json()["states"]
        assert len(res_pub_locs_after.json()["states"]) == 27

        # 5. Public jobs-page endpoint also excludes Goa from active list
        res_pub_jobs = await client.get("/api/v1/public/website-content/jobs-page")
        assert res_pub_jobs.status_code == 200
        active_pub_names = [l["name"] for l in res_pub_jobs.json()["locations"]]
        assert "Goa" not in active_pub_names

        # 6. Admin resets locations to all active
        res_reset_locs = await client.post("/api/v1/admin/website-content/jobs-page/locations/reset", headers=admin_headers)
        assert res_reset_locs.status_code == 200
        assert all(l["is_active"] for l in res_reset_locs.json())

        # Public now has Goa back
        res_pub_locs_reset = await client.get("/api/v1/public/job-locations")
        assert "Goa" in res_pub_locs_reset.json()["states"]
        assert len(res_pub_locs_reset.json()["states"]) == 28


@pytest.mark.asyncio
async def test_jobs_page_security_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Candidate token
        cand_token = await get_candidate_token(client)
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Candidate forbidden from admin jobs page
        res_cand = await client.patch(
            "/api/v1/admin/website-content/jobs-page/hero",
            json={"heading": "Unauthorized Hack"},
            headers=cand_headers,
        )
        assert res_cand.status_code in [401, 403]

        # 2. Unauthenticated user unauthorized
        res_unauth = await client.patch(
            "/api/v1/admin/website-content/jobs-page/hero",
            json={"heading": "Unauthorized Hack"},
        )
        assert res_unauth.status_code in [401, 403]


@pytest.mark.asyncio
async def test_admin_about_us_fetch_and_section_updates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin loads full About Us settings
        res = await client.get("/api/v1/admin/website-content/about-us", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "hero" in data
        assert "whatWeStandFor" in data
        assert "team" in data
        assert "leadershipMessages" in data
        assert "partners" in data
        assert len(data["whatWeStandFor"]["cards"]) == 3
        assert len(data["team"]["members"]) >= 4
        assert len(data["leadershipMessages"]["messages"]) >= 2
        assert len(data["partners"]["list"]) >= 13

        # 2. Update Hero
        res_hero = await client.patch(
            "/api/v1/admin/website-content/about-us/hero",
            json={
                "badge": "Empowering Future Generations",
                "heading": "Unlocking Careers Across Andhra Pradesh",
                "description": "Connecting skilled students and job seekers directly to vetted corporate partners.",
            },
            headers=admin_headers,
        )
        assert res_hero.status_code == 200
        hero_data = res_hero.json()["hero"]
        assert hero_data["badge"] == "Empowering Future Generations"
        assert hero_data["heading"] == "Unlocking Careers Across Andhra Pradesh"

        # 3. Update Principles (What We Stand For)
        updated_cards = [
            {"id": "wwsf-1", "icon": "ShieldCheck", "title": "Zero Placement Fees", "desc": "100% free employment assistance for all applicants.", "color": "primary"},
            {"id": "wwsf-2", "icon": "Target", "title": "Direct Corporate Connect", "desc": "Direct engagement with vetted HR teams.", "color": "success"},
            {"id": "wwsf-3", "icon": "Users", "title": "Inclusive District Melas", "desc": "Reaching rural and semi-urban talents.", "color": "warning"},
        ]
        res_wwsf = await client.patch(
            "/api/v1/admin/website-content/about-us/principles",
            json={
                "heading": "Our Core Values & Principles",
                "description": "Principles driving every job fair and student counseling drive.",
                "cards": updated_cards,
            },
            headers=admin_headers,
        )
        assert res_wwsf.status_code == 200
        wwsf_data = res_wwsf.json()["whatWeStandFor"]
        assert wwsf_data["heading"] == "Our Core Values & Principles"
        assert len(wwsf_data["cards"]) == 3
        assert wwsf_data["cards"][0]["title"] == "Zero Placement Fees"

        # 4. Update Team
        team_members = [
            {
                "id": "team-test-1",
                "name": "Dr. Ramesh Sundaram",
                "role": "Executive Chairman & Founder",
                "organization": "NTR Vikasa Skill Center",
                "bio": "25+ years driving state employment and youth development.",
                "image": None,
            },
            {
                "id": "team-test-2",
                "name": "Ananya Deshmukh",
                "role": "Vice President of Technology",
                "organization": "NTR Vikasa",
                "bio": "Tech leader driving job matching algorithms.",
                "image": None,
            },
        ]
        res_team = await client.put(
            "/api/v1/admin/website-content/about-us/team",
            json={
                "badge": "Leadership Council",
                "heading": "Executive Leadership Team",
                "description": "Visionary leaders guiding NTR Vikasa employment operations.",
                "members": team_members,
            },
            headers=admin_headers,
        )
        assert res_team.status_code == 200
        team_data = res_team.json()["team"]
        assert team_data["heading"] == "Executive Leadership Team"
        assert len(team_data["members"]) == 2
        assert team_data["members"][0]["name"] == "Dr. Ramesh Sundaram"

        # 5. Update Leadership Statements
        leaders = [
            {
                "id": "msg-1",
                "name": "K Lacha Rao",
                "designation": "Honorable Chairperson",
                "role": "Honorable Chairperson",
                "organization": "NTR Vikasa Jobs",
                "image": None,
                "initials": "KLR",
                "headerBg": "#0f2a59",
                "message": "Providing world-class skilling and placement drives across all AP districts.",
                "fullMessage": "Providing world-class skilling and placement drives across all AP districts with utmost integrity.",
                "hasViewAction": False,
            }
        ]
        res_lead = await client.put(
            "/api/v1/admin/website-content/about-us/leadership",
            json={
                "badge": "PATRONS",
                "heading": "Visionary Messages",
                "description": "Inspiring words from project leadership",
                "messages": leaders,
            },
            headers=admin_headers,
        )
        assert res_lead.status_code == 200
        lead_data = res_lead.json()["leadershipMessages"]
        assert lead_data["badge"] == "PATRONS"
        assert len(lead_data["messages"]) == 1

        # 6. Update Partners with one hidden partner
        partners_list = [
            {"id": "p-1", "name": "Hyundai MOBIS", "logoText": "HYUNDAI MOBIS", "active": True, "order": 1},
            {"id": "p-2", "name": "ISUZU Motors", "logoText": "ISUZU", "active": False, "order": 2},  # HIDDEN
            {"id": "p-3", "name": "MedPlus Health", "logoText": "MedPlus+", "active": True, "order": 3},
        ]
        res_partners = await client.put(
            "/api/v1/admin/website-content/about-us/partners",
            json={
                "heading": "Our Corporate Training Network",
                "description": "Leading industrial employers committed to hiring NTR Vikasa candidates.",
                "list": partners_list,
            },
            headers=admin_headers,
        )
        assert res_partners.status_code == 200
        partners_data = res_partners.json()["partners"]
        assert len(partners_data["list"]) == 3
        # In admin view, all partners including inactive are returned
        assert any(p["active"] is False for p in partners_data["list"])


@pytest.mark.asyncio
async def test_public_about_us_visibility_and_partner_filtering():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test /api/v1/public/website-content/about-us
        res_pub1 = await client.get("/api/v1/public/website-content/about-us")
        assert res_pub1.status_code == 200
        data1 = res_pub1.json()

        # In public view, inactive partner ISUZU must be filtered out!
        pub_partner_names = [p["name"] for p in data1["partners"]["list"]]
        assert "Hyundai MOBIS" in pub_partner_names
        assert "MedPlus Health" in pub_partner_names
        assert "ISUZU Motors" not in pub_partner_names
        assert all(p.get("active") is not False for p in data1["partners"]["list"])

        # 2. Test alias /api/v1/public/about-us
        res_pub2 = await client.get("/api/v1/public/about-us")
        assert res_pub2.status_code == 200
        data2 = res_pub2.json()
        assert data2["hero"]["heading"] == data1["hero"]["heading"]
        assert "ISUZU Motors" not in [p["name"] for p in data2["partners"]["list"]]


@pytest.mark.asyncio
async def test_about_us_reset_defaults_and_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        cand_token = await get_candidate_token(client)
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Reset defaults
        res_reset = await client.post(
            "/api/v1/admin/website-content/about-us/reset-defaults",
            headers=admin_headers,
        )
        assert res_reset.status_code == 200
        reset_data = res_reset.json()
        assert reset_data["hero"]["badge"] == "Our Mission & Impact"
        assert reset_data["hero"]["heading"] == "Bridging Talent with Opportunity Across India"
        assert len(reset_data["partners"]["list"]) == 13

        # 2. Candidate unauthorized
        res_cand = await client.patch(
            "/api/v1/admin/website-content/about-us/hero",
            json={"badge": "Bad", "heading": "Bad", "description": "Bad"},
            headers=cand_headers,
        )
        assert res_cand.status_code in [401, 403]

        # 3. Unauthenticated unauthorized
        res_unauth = await client.patch(
            "/api/v1/admin/website-content/about-us/hero",
            json={"badge": "Bad", "heading": "Bad", "description": "Bad"},
        )
        assert res_unauth.status_code in [401, 403]

        # 4. Validation error on empty fields
        res_val = await client.patch(
            "/api/v1/admin/website-content/about-us/hero",
            json={"badge": "", "heading": "", "description": ""},
            headers=admin_headers,
        )
        assert res_val.status_code == 422


@pytest.mark.asyncio
async def test_job_melas_hero_get_and_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Admin gets current hero
        res_get = await client.get("/api/v1/admin/website-content/job-melas/hero", headers=admin_headers)
        assert res_get.status_code == 200
        hero_data = res_get.json()
        assert "badge" in hero_data
        assert "heading" in hero_data
        assert "description" in hero_data
        assert "hero" in hero_data
        assert hero_data["hero"]["badge"] == hero_data["badge"]

        # 2. Admin updates hero
        update_payload = {
            "badge": "AP State Mega Drives 2026",
            "heading": "Statewide NTR Vikasa Job Melas",
            "description": "Connecting 50,000+ job seekers with leading multinational companies across all 26 districts of Andhra Pradesh.",
        }
        res_update = await client.patch(
            "/api/v1/admin/website-content/job-melas/hero",
            json=update_payload,
            headers=admin_headers,
        )
        assert res_update.status_code == 200
        updated = res_update.json()
        assert updated["badge"] == update_payload["badge"]
        assert updated["heading"] == update_payload["heading"]
        assert updated["description"] == update_payload["description"]
        assert updated["hero"]["badge"] == update_payload["badge"]

        # 3. Public endpoint reflects updated hero
        res_pub = await client.get("/api/v1/public/website-content/job-melas/hero")
        assert res_pub.status_code == 200
        pub_data = res_pub.json()
        assert pub_data["badge"] == update_payload["badge"]
        assert pub_data["heading"] == update_payload["heading"]
        assert pub_data["description"] == update_payload["description"]

        # 4. Direct alias reflects updated hero
        res_pub_direct = await client.get("/api/v1/public/job-melas/hero")
        assert res_pub_direct.status_code == 200
        assert res_pub_direct.json()["heading"] == update_payload["heading"]


@pytest.mark.asyncio
async def test_job_melas_hero_reset_defaults_and_security():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        cand_token = await get_candidate_token(client)
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Reset defaults
        res_reset = await client.post(
            "/api/v1/admin/website-content/job-melas/hero/reset-defaults",
            headers=admin_headers,
        )
        assert res_reset.status_code == 200
        reset_data = res_reset.json()
        assert reset_data["badge"] == "Nationwide Recruitment Drives"
        assert reset_data["heading"] == "Mega Job Melas & Career Fairs"
        assert "100+ hiring companies" in reset_data["description"]

        # 2. Public view also reflects reset defaults
        res_pub = await client.get("/api/v1/public/website-content/job-melas/hero")
        assert res_pub.status_code == 200
        assert res_pub.json()["badge"] == "Nationwide Recruitment Drives"

        # 3. Candidate unauthorized
        res_cand = await client.patch(
            "/api/v1/admin/website-content/job-melas/hero",
            json={"badge": "Unauthorized", "heading": "Fail", "description": "Fail"},
            headers=cand_headers,
        )
        assert res_cand.status_code in [401, 403]

        # 4. Unauthenticated unauthorized
        res_unauth = await client.patch(
            "/api/v1/admin/website-content/job-melas/hero",
            json={"badge": "Unauthorized", "heading": "Fail", "description": "Fail"},
        )
        assert res_unauth.status_code in [401, 403]

        # 5. Validation error on empty fields
        res_val = await client.patch(
            "/api/v1/admin/website-content/job-melas/hero",
            json={"badge": "", "heading": "", "description": ""},
            headers=admin_headers,
        )
        assert res_val.status_code == 422


@pytest.mark.asyncio
async def test_job_melas_published_events_public_consistency():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Public events list
        res = await client.get("/api/v1/job-melas")
        assert res.status_code == 200
        events = res.json()
        assert isinstance(events, list)
        for ev in events:
            assert ev["status"] in ["PUBLISHED", "ACTIVE", "REGISTRATION_OPEN", "UPCOMING", "APPROVED"]


@pytest.mark.asyncio
async def test_skill_development_public_and_admin_read():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Public read all 6 sections (/cms/skills)
        res_pub = await client.get("/api/v1/cms/skills")
        assert res_pub.status_code == 200
        data = res_pub.json()
        assert "skills_hero" in data or "hero" in data
        assert "skills_highlights" in data or "highlights" in data
        assert "skills_mission" in data or "empoweringSkills" in data
        assert "skills_pathway" in data or "trainingJourney" in data
        assert "skills_advantages" in data or "whyChoose" in data
        assert "skills_programs" in data or "programsWeOffer" in data
        assert len(data["skills_highlights"]) == 4

        # 2. Public read alias (/public/website-content/skills)
        res_pub_alias = await client.get("/api/v1/public/website-content/skills")
        assert res_pub_alias.status_code == 200
        assert res_pub_alias.json()["hero"]["heading"] == data["hero"]["heading"]

        # 3. Public read single section
        res_sec = await client.get("/api/v1/cms/skills/skills_hero")
        assert res_sec.status_code == 200
        sec_data = res_sec.json()
        assert sec_data["section_key"] == "skills_hero"
        assert "heading" in sec_data["content"]

        # 4. Admin read all
        res_admin = await client.get("/api/v1/admin/cms/skills", headers=admin_headers)
        assert res_admin.status_code == 200
        admin_data = res_admin.json()
        assert len(admin_data["highlights"]) == 4


@pytest.mark.asyncio
async def test_skill_development_update_sections_and_persistence():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Update hero
        hero_payload = {
            "badge": "AP State Skill Mission 2026",
            "heading": "Certified Employment Training Programs",
            "description": "Comprehensive practical curriculum designed for fast-track placement across Vijayawada, Vizag, and all AP districts.",
            "exploreBtnText": "Browse Tracks",
            "viewCoursesBtnText": "View All Courses",
        }
        res_hero = await client.put(
            "/api/v1/admin/cms/skills/skills_hero",
            json=hero_payload,
            headers=admin_headers,
        )
        assert res_hero.status_code == 200
        assert res_hero.json()["content"]["heading"] == hero_payload["heading"]

        # 2. Update 4 highlights
        highlights_payload = [
            {"id": "hl-1", "icon": "Award", "title": "National Certification", "subtitle": "NSDC / Skill India"},
            {"id": "hl-2", "icon": "TrendingUp", "title": "Guaranteed Support", "subtitle": "Spot Recruitment Melas"},
            {"id": "hl-3", "icon": "BookOpen", "title": "Modern Labs", "subtitle": "70% Hands-On Practical"},
            {"id": "hl-4", "icon": "Users", "title": "Corporate Mentors", "subtitle": "Industry Veterans"},
        ]
        res_hl = await client.put(
            "/api/v1/admin/cms/skills/skills_highlights",
            json=highlights_payload,
            headers=admin_headers,
        )
        assert res_hl.status_code == 200
        assert len(res_hl.json()["content"]) == 4

        # 3. Update mission with 3 pillars
        mission_payload = {
            "badge": "Our Institutional Mission",
            "heading": "Empowering Talent for Modern Careers",
            "description": "Transforming ambitious job seekers into highly competitive technical candidates.",
            "cards": [
                {"id": "es-1", "icon": "Code2", "title": "Market-Driven Learning", "desc": "Curated with tech leaders."},
                {"id": "es-2", "icon": "Laptop", "title": "Practical Lab Exposure", "desc": "Live real-world capstones."},
                {"id": "es-3", "icon": "TrendingUp", "title": "Direct Placement Drives", "desc": "Job melas across AP."},
            ],
        }
        res_ms = await client.put(
            "/api/v1/admin/cms/skills/skills_mission",
            json=mission_payload,
            headers=admin_headers,
        )
        assert res_ms.status_code == 200
        assert len(res_ms.json()["content"]["cards"]) == 3

        # 4. Update pathway with 6 steps
        pathway_payload = {
            "badge": "Candidate Roadmap",
            "heading": "Structured Path to Career Success",
            "description": "Six comprehensive milestones from onboarding to offer letters.",
            "steps": [
                {"step": "01", "title": "Select Specialization", "desc": "Choose domain."},
                {"step": "02", "title": "Admission & Evaluation", "desc": "Free registration."},
                {"step": "03", "title": "Intensive Lab Training", "desc": "Hands-on projects."},
                {"step": "04", "title": "Official Certification", "desc": "Earn NSDC credentials."},
                {"step": "05", "title": "Corporate Interview Prep", "desc": "Mock interviews & resume review."},
                {"step": "06", "title": "Direct Placement Drives", "desc": "Exclusive hiring interviews."},
            ],
        }
        res_pw = await client.put(
            "/api/v1/admin/cms/skills/skills_pathway",
            json=pathway_payload,
            headers=admin_headers,
        )
        assert res_pw.status_code == 200
        assert len(res_pw.json()["content"]["steps"]) == 6

        # 5. Update advantages with 6 cards
        adv_payload = {
            "badge": "Why NTR VIKASA",
            "heading": "The NTR VIKASA Advantage",
            "description": "Proven track record of placing thousands of candidates.",
            "cards": [
                {"icon": "Award", "title": "Govt Recognized", "desc": "Certified credentials."},
                {"icon": "Laptop", "title": "Practical Labs", "desc": "Interactive training."},
                {"icon": "Users", "title": "Certified Instructors", "desc": "Industry experts."},
                {"icon": "TrendingUp", "title": "Placement Direct", "desc": "Job fair invitations."},
                {"icon": "ShieldCheck", "title": "Free / Subsidized", "desc": "Zero fees for candidates."},
                {"icon": "Sparkles", "title": "Modern Tools", "desc": "AI & productivity software."},
            ],
        }
        res_adv = await client.put(
            "/api/v1/admin/cms/skills/skills_advantages",
            json=adv_payload,
            headers=admin_headers,
        )
        assert res_adv.status_code == 200
        assert len(res_adv.json()["content"]["cards"]) == 6

        # 6. Update programs with 8 categories
        prog_payload = {
            "badge": "Training Tracks",
            "heading": "Domain Programs We Offer",
            "description": "Eight specialized sectors designed for in-demand employment.",
            "categories": [
                {"id": "it", "name": "Software & Web Development", "icon": "Code2", "desc": "Fullstack & Cloud", "count": "4 Courses"},
                {"id": "data-ai", "name": "Data Analytics & AI", "icon": "Database", "desc": "Power BI & SQL", "count": "3 Courses"},
                {"id": "ai-tools", "name": "Generative AI Tools", "icon": "Sparkles", "desc": "Prompt Engineering", "count": "2 Courses"},
                {"id": "banking", "name": "Banking & Financial Services", "icon": "Landmark", "desc": "BFSI operations", "count": "3 Courses"},
                {"id": "accounting", "name": "Accounting & GST", "icon": "Calculator", "desc": "Tally Prime & Excel", "count": "2 Courses"},
                {"id": "core-eng", "name": "Electrical & Automation", "icon": "Cpu", "desc": "PLC & SCADA", "count": "3 Courses"},
                {"id": "healthcare", "name": "Hospital Support & Healthcare", "icon": "Activity", "desc": "EMR & Billing", "count": "2 Courses"},
                {"id": "marketing", "name": "Digital Marketing & Sales", "icon": "Megaphone", "desc": "SEO & Performance Ads", "count": "3 Courses"},
            ],
        }
        res_prog = await client.put(
            "/api/v1/admin/cms/skills/skills_programs",
            json=prog_payload,
            headers=admin_headers,
        )
        assert res_prog.status_code == 200
        assert len(res_prog.json()["content"]["categories"]) == 8

        # 7. Verify public endpoint reflects all updates
        res_pub_verify = await client.get("/api/v1/cms/skills")
        assert res_pub_verify.status_code == 200
        pub_all = res_pub_verify.json()
        assert pub_all["hero"]["heading"] == hero_payload["heading"]
        assert pub_all["highlights"][0]["title"] == "National Certification"
        assert pub_all["empoweringSkills"]["heading"] == mission_payload["heading"]
        assert pub_all["trainingJourney"]["heading"] == pathway_payload["heading"]
        assert pub_all["whyChoose"]["heading"] == adv_payload["heading"]
        assert pub_all["programsWeOffer"]["heading"] == prog_payload["heading"]


@pytest.mark.asyncio
async def test_skill_development_validations_and_item_counts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Invalid section key
        res_invalid_key = await client.put(
            "/api/v1/admin/cms/skills/non_existent_section",
            json={"badge": "Test"},
            headers=admin_headers,
        )
        assert res_invalid_key.status_code == 422

        # 2. Highlights with 3 items (must be exactly 4)
        res_hl_bad = await client.put(
            "/api/v1/admin/cms/skills/skills_highlights",
            json=[
                {"id": "1", "icon": "Award", "title": "One", "subtitle": "Sub"},
                {"id": "2", "icon": "Award", "title": "Two", "subtitle": "Sub"},
                {"id": "3", "icon": "Award", "title": "Three", "subtitle": "Sub"},
            ],
            headers=admin_headers,
        )
        assert res_hl_bad.status_code == 422

        # 3. Mission with 2 pillars (must be exactly 3)
        res_ms_bad = await client.put(
            "/api/v1/admin/cms/skills/skills_mission",
            json={
                "badge": "B",
                "heading": "H",
                "description": "D",
                "cards": [
                    {"id": "1", "title": "One", "desc": "Desc"},
                    {"id": "2", "title": "Two", "desc": "Desc"},
                ],
            },
            headers=admin_headers,
        )
        assert res_ms_bad.status_code == 422

        # 4. Pathway with 5 steps (must be exactly 6)
        res_pw_bad = await client.put(
            "/api/v1/admin/cms/skills/skills_pathway",
            json={
                "badge": "B",
                "heading": "H",
                "description": "D",
                "steps": [
                    {"step": "01", "title": "1", "desc": "D"},
                    {"step": "02", "title": "2", "desc": "D"},
                    {"step": "03", "title": "3", "desc": "D"},
                    {"step": "04", "title": "4", "desc": "D"},
                    {"step": "05", "title": "5", "desc": "D"},
                ],
            },
            headers=admin_headers,
        )
        assert res_pw_bad.status_code == 422

        # 5. Advantages with 5 cards (must be exactly 6)
        res_adv_bad = await client.put(
            "/api/v1/admin/cms/skills/skills_advantages",
            json={
                "badge": "B",
                "heading": "H",
                "description": "D",
                "cards": [
                    {"icon": "Award", "title": "1", "desc": "D"},
                    {"icon": "Award", "title": "2", "desc": "D"},
                    {"icon": "Award", "title": "3", "desc": "D"},
                    {"icon": "Award", "title": "4", "desc": "D"},
                    {"icon": "Award", "title": "5", "desc": "D"},
                ],
            },
            headers=admin_headers,
        )
        assert res_adv_bad.status_code == 422

        # 6. Programs with 7 categories (must be exactly 8)
        res_prog_bad = await client.put(
            "/api/v1/admin/cms/skills/skills_programs",
            json={
                "badge": "B",
                "heading": "H",
                "description": "D",
                "categories": [
                    {"id": "1", "name": "1", "desc": "D"},
                    {"id": "2", "name": "2", "desc": "D"},
                    {"id": "3", "name": "3", "desc": "D"},
                    {"id": "4", "name": "4", "desc": "D"},
                    {"id": "5", "name": "5", "desc": "D"},
                    {"id": "6", "name": "6", "desc": "D"},
                    {"id": "7", "name": "7", "desc": "D"},
                ],
            },
            headers=admin_headers,
        )
        assert res_prog_bad.status_code == 422


@pytest.mark.asyncio
async def test_skill_development_security_and_reset_defaults():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token = await get_admin_token(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        cand_token = await get_candidate_token(client)
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Unauthenticated cannot update
        res_unauth = await client.put(
            "/api/v1/admin/cms/skills/skills_hero",
            json={"badge": "B", "heading": "H", "description": "D"},
        )
        assert res_unauth.status_code in [401, 403]

        # 2. Candidate cannot update
        res_cand = await client.put(
            "/api/v1/admin/cms/skills/skills_hero",
            json={"badge": "B", "heading": "H", "description": "D"},
            headers=cand_headers,
        )
        assert res_cand.status_code in [401, 403]

        # 3. Reset hero section only
        res_reset_hero = await client.post(
            "/api/v1/admin/cms/skills/skills_hero/reset",
            headers=admin_headers,
        )
        assert res_reset_hero.status_code == 200
        hero_reset = res_reset_hero.json()
        assert hero_reset["content"]["heading"] == "Skill Development & Training Programs"

        # 4. Verify other section (e.g. highlights) was NOT reset
        res_hl = await client.get("/api/v1/cms/skills/skills_highlights")
        assert res_hl.status_code == 200
        assert res_hl.json()["content"][0]["title"] == "National Certification"

        # 5. Full reset restores all sections
        res_reset_all = await client.post(
            "/api/v1/admin/cms/skills/reset",
            headers=admin_headers,
        )
        assert res_reset_all.status_code == 200
        all_reset = res_reset_all.json()
        assert all_reset["highlights"][0]["title"] == "Government Recognized"



