import asyncio
import sys
import httpx
sys.path.insert(0, ".")
from app.core.security import create_access_token

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_apis():
    # Generate token for candidate1 (user_id: 7e0c7911-2578-43d6-93d8-671bc1ad9ae9)
    cand1_token = create_access_token(subject="7e0c7911-2578-43d6-93d8-671bc1ad9ae9", role="CANDIDATE", email="candidate1@ntrvikasa.com")
    headers = {"Authorization": f"Bearer {cand1_token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Test unauthenticated request -> 401
        res = await client.get("/candidate/interviews")
        print("1. Unauthenticated GET /candidate/interviews status:", res.status_code)
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

        # 2. Test authenticated list
        res = await client.get("/candidate/interviews", headers=headers)
        print("2. Authenticated GET /candidate/interviews status:", res.status_code)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        print("   Total interviews:", data["total"])
        print("   Counts:", data["counts"])
        print("   Items count:", len(data["items"]))
        assert data["total"] >= 3, f"Expected total >= 3, got {data['total']}"
        assert data["counts"]["all"] >= 3
        assert data["counts"]["upcoming"] >= 1
        assert data["counts"]["today"] >= 1
        assert data["counts"]["completed"] >= 1

        # 3. Test filter status=UPCOMING
        res_up = await client.get("/candidate/interviews?status=UPCOMING", headers=headers)
        assert res_up.status_code == 200
        up_data = res_up.json()
        print("3. UPCOMING filter items:", len(up_data["items"]))
        assert len(up_data["items"]) >= 1

        # 4. Test filter status=TODAY
        res_today = await client.get("/candidate/interviews?status=TODAY", headers=headers)
        assert res_today.status_code == 200
        today_data = res_today.json()
        print("4. TODAY filter items:", len(today_data["items"]))
        assert len(today_data["items"]) >= 1

        # 5. Test filter status=COMPLETED
        res_comp = await client.get("/candidate/interviews?status=COMPLETED", headers=headers)
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        print("5. COMPLETED filter items:", len(comp_data["items"]))
        assert len(comp_data["items"]) >= 1

        # 6. Test search
        res_search = await client.get("/candidate/interviews?search=Infosys", headers=headers)
        assert res_search.status_code == 200
        search_data = res_search.json()
        print("6. Search 'Infosys' items:", len(search_data["items"]))
        assert len(search_data["items"]) >= 1
        assert "Infosys" in search_data["items"][0]["company_name"]

        # 7. Test single interview detail
        first_id = data["items"][0]["id"]
        res_detail = await client.get(f"/candidate/interviews/{first_id}", headers=headers)
        print("7. GET single interview detail status:", res_detail.status_code)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        print("   Detail title:", detail["title"], "| company:", detail["company_name"], "| meeting_link:", detail["meeting_link"])
        assert detail["id"] == first_id

        # 8. Test 404 for non-existent interview
        res_404 = await client.get("/candidate/interviews/non-existent-id", headers=headers)
        print("8. Non-existent interview status:", res_404.status_code)
        assert res_404.status_code == 404

    print("\n✅ All Candidate Interviews Backend API Tests Passed 100%!")

if __name__ == "__main__":
    asyncio.run(test_apis())
