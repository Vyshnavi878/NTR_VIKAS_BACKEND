import asyncio
import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000/api/v1"


async def run_tests():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print("\n--- 1. Login as Primary Recruiter ---")
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "recruiter1@ntrvikasa.com",
                "password": "password123",
                "role": "RECRUITER",
            },
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        tokens = login_resp.json()
        token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Logged in successfully as recruiter1.")

        print("\n--- 2. GET Recruiter Profile ---")
        prof_resp = await client.get("/recruiter/settings/profile", headers=headers)
        assert prof_resp.status_code == 200, f"Get profile failed: {prof_resp.text}"
        prof = prof_resp.json()
        print("Profile fetched:", prof)
        assert prof["work_email"] == "recruiter1@ntrvikasa.com"
        assert prof["company_name"] != ""
        company_id = prof["company_id"]

        print("\n--- 3. PATCH Recruiter Profile ---")
        patch_resp = await client.patch(
            "/recruiter/settings/profile",
            headers=headers,
            json={
                "full_name": "Arjun Reddy Updated",
                "designation": "VP of Talent Acquisition",
                "phone": "+91 98765 00999",
            },
        )
        assert patch_resp.status_code == 200, f"Patch profile failed: {patch_resp.text}"
        updated_prof = patch_resp.json()
        assert updated_prof["full_name"] == "Arjun Reddy Updated"
        assert updated_prof["designation"] == "VP of Talent Acquisition"
        print("Profile updated successfully:", updated_prof["full_name"], updated_prof["designation"])

        print("\n--- 4. GET Team Members ---")
        team_resp = await client.get("/recruiter/settings/team", headers=headers)
        assert team_resp.status_code == 200, f"Get team failed: {team_resp.text}"
        team = team_resp.json()
        print(f"Team members count: {len(team)}")
        assert any(m["work_email"] == "recruiter1@ntrvikasa.com" for m in team)

        print("\n--- 5. Invite New Team Member ---")
        invite_email = f"newhire_{asyncio.get_event_loop().time():.0f}@abctech.com"
        inv_resp = await client.post(
            "/recruiter/settings/team/invitations",
            headers=headers,
            json={
                "name": "Kavitha Rao",
                "email": invite_email,
                "role": "Technical Recruiter",
            },
        )
        assert inv_resp.status_code == 201, f"Invite failed: {inv_resp.text}"
        inv_data = inv_resp.json()
        print("Invitation created:", inv_data)
        raw_token = inv_data["invitation_token"]
        assert raw_token is not None

        print("\n--- 6. Duplicate Invite Check ---")
        dup_resp = await client.post(
            "/recruiter/settings/team/invitations",
            headers=headers,
            json={
                "name": "Arjun Reddy",
                "email": "recruiter1@ntrvikasa.com",
                "role": "Technical Recruiter",
            },
        )
        assert dup_resp.status_code == 409, f"Expected 409 conflict, got: {dup_resp.status_code}"
        print("Duplicate invite correctly rejected with 409 Conflict.")

        print("\n--- 7. Validate Invitation Token ---")
        val_resp = await client.get(f"/auth/invitations/{raw_token}/validate")
        assert val_resp.status_code == 200, f"Validation failed: {val_resp.text}"
        val_data = val_resp.json()
        assert val_data["valid"] is True
        assert val_data["email"] == invite_email
        print("Token validation passed:", val_data)

        print("\n--- 8. Accept Invitation & Join Existing Company ---")
        accept_resp = await client.post(
            "/auth/recruiter/invitations/accept",
            json={
                "token": raw_token,
                "password": "newpassword123",
                "confirm_password": "newpassword123",
            },
        )
        assert accept_resp.status_code == 200, f"Accept invitation failed: {accept_resp.text}"
        new_user_data = accept_resp.json()
        print("Invitation accepted! User details:", new_user_data)
        new_token = new_user_data["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        print("\n--- 9. Verify Invited User Belongs to SAME Company ---")
        invited_prof_resp = await client.get("/recruiter/settings/profile", headers=new_headers)
        assert invited_prof_resp.status_code == 200, f"Invited member get profile failed: {invited_prof_resp.text}"
        invited_prof = invited_prof_resp.json()
        print("Invited member profile:", invited_prof)
        assert invited_prof["company_id"] == company_id, "Invited recruiter must belong to the SAME company!"
        print("Verified: Both recruiters share company_id:", company_id)

        print("\n--- 10. Notification Preferences Persistence ---")
        notif_get = await client.get("/recruiter/settings/notifications", headers=headers)
        assert notif_get.status_code == 200
        print("Initial notifications:", notif_get.json())

        notif_patch = await client.patch(
            "/recruiter/settings/notifications",
            headers=headers,
            json={
                "applicantAlerts": False,
                "weeklyDigest": False,
            },
        )
        assert notif_patch.status_code == 200
        updated_notifs = notif_patch.json()
        assert updated_notifs["applicantAlerts"] is False
        assert updated_notifs["weeklyDigest"] is False
        print("Patched notification preferences:", updated_notifs)

        # Refetch to confirm persistence
        notif_refetch = await client.get("/recruiter/settings/notifications", headers=headers)
        assert notif_refetch.json()["applicantAlerts"] is False
        print("Verified persistence in MySQL for notification preferences.")

        print("\n--- 11. Change Password ---")
        pwd_resp = await client.post(
            "/auth/change-password",
            headers=new_headers,
            json={
                "currentPassword": "newpassword123",
                "newPassword": "newpassword456",
                "confirmPassword": "newpassword456",
            },
        )
        assert pwd_resp.status_code == 200, f"Password change failed: {pwd_resp.text}"
        print("Password changed successfully:", pwd_resp.json())

        # Test login with new password
        new_login = await client.post(
            "/auth/login",
            json={
                "email": invite_email,
                "password": "newpassword456",
                "role": "RECRUITER",
            },
        )
        assert new_login.status_code == 200, "Login with new password should succeed!"
        print("Login with new password confirmed!")

    print("\nALL RECRUITER SETTINGS BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_tests())
