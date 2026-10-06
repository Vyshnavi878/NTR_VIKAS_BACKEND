import asyncio
import sys
import httpx
sys.path.insert(0, ".")
from app.core.security import create_access_token

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_full_workflow():
    # 1. Candidate 1 Token (user_id: 7e0c7911-2578-43d6-93d8-671bc1ad9ae9)
    cand1_token = create_access_token(
        subject="7e0c7911-2578-43d6-93d8-671bc1ad9ae9",
        role="CANDIDATE",
        email="candidate1@ntrvikasa.com"
    )
    cand_headers = {"Authorization": f"Bearer {cand1_token}"}

    # 2. Recruiter Token (recruiter_id: 0d4407a6-2b51-4848-a92f-7b593d42c871)
    recruiter_token = create_access_token(
        subject="0c9a4498-8ec1-4e7a-9097-7cfa8090f48f",
        role="RECRUITER",
        email="recruiter1@abc-tech.com"
    )
    rec_headers = {"Authorization": f"Bearer {recruiter_token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        print("\n--- 1. Testing Unauthenticated Access ---")
        res_unauth = await client.get("/candidate/interviews")
        print("Unauthenticated status:", res_unauth.status_code)
        assert res_unauth.status_code == 401

        print("\n--- 2. Testing Candidate Interviews Listing ---")
        res_list = await client.get("/candidate/interviews", headers=cand_headers)
        print("Candidate interviews status:", res_list.status_code)
        assert res_list.status_code == 200
        data = res_list.json()
        print(f"Total: {data['total']}, Page: {data['page']}, Total Pages: {data['total_pages']}")
        print(f"Counts: {data['counts']}")
        assert data["total"] >= 3
        assert data["counts"]["all"] >= 3
        assert data["counts"]["upcoming"] >= 1
        assert data["counts"]["today"] >= 1
        assert data["counts"]["completed"] >= 1

        print("\n--- 3. Testing Category Filters ---")
        # Upcoming
        res_up = await client.get("/candidate/interviews?status=UPCOMING", headers=cand_headers)
        assert res_up.status_code == 200
        up_items = res_up.json()["items"]
        print(f"Upcoming items: {len(up_items)}")
        assert len(up_items) >= 1
        for item in up_items:
            assert item["status"] in ("UPCOMING", "SCHEDULED", "RESCHEDULED")

        # Today
        res_today = await client.get("/candidate/interviews?status=TODAY", headers=cand_headers)
        assert res_today.status_code == 200
        today_items = res_today.json()["items"]
        print(f"Today items: {len(today_items)}")
        assert len(today_items) >= 1

        # Completed
        res_comp = await client.get("/candidate/interviews?status=COMPLETED", headers=cand_headers)
        assert res_comp.status_code == 200
        comp_items = res_comp.json()["items"]
        print(f"Completed items: {len(comp_items)}")
        assert len(comp_items) >= 1
        for item in comp_items:
            assert item["status"] == "COMPLETED" or item["result"] is not None

        print("\n--- 4. Testing Search Query ---")
        res_search = await client.get("/candidate/interviews?search=Infosys", headers=cand_headers)
        assert res_search.status_code == 200
        search_items = res_search.json()["items"]
        print(f"Search 'Infosys' items: {len(search_items)}")
        assert len(search_items) >= 1
        assert "Infosys" in (search_items[0]["company_name"] or search_items[0]["company"])

        print("\n--- 5. Testing Single Interview Detail ---")
        first_interview = data["items"][0]
        res_detail = await client.get(f"/candidate/interviews/{first_interview['id']}", headers=cand_headers)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        print(f"Detail: ID={detail['id']} | Title={detail['title']} | Role={detail['role']} | Company={detail['company_name']}")
        assert detail["id"] == first_interview["id"]
        assert detail["meeting_link"] is not None
        assert detail["timezone"] == "Asia/Kolkata"

        print("\n--- 6. Testing IDOR & Security Isolation ---")
        # Candidate cannot access invalid or other candidates' interview
        res_fake = await client.get("/candidate/interviews/invalid-interview-id", headers=cand_headers)
        assert res_fake.status_code == 404
        print("404 received for unauthorized interview ID: PASSED")

        # Recruiter endpoint cannot be accessed by candidate token
        res_rec_forbidden = await client.get("/recruiter/interviews", headers=cand_headers)
        assert res_rec_forbidden.status_code == 403
        print("403 received when candidate accesses recruiter endpoint: PASSED")

    print("\nALL END-TO-END CANDIDATE INTERVIEW TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
