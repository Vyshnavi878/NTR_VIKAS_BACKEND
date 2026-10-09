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
