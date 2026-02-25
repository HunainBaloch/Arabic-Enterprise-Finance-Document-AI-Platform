import httpx
import asyncio

async def main():
    # Login as admin
    login_url = "http://127.0.0.1:8000/api/v1/login/access-token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(login_url, data={"username": "admin@test.com", "password": "AdminPass123!"})
        if resp.status_code != 200:
            print("Login failed:", resp.text)
            return

        token = resp.json()["access_token"]
        print("Logged in!")

        # Create dummy file
        # Create a VALID dummy PDF file using fitz
        import fitz
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((50, 50), "VENDOR: Acme Corp\nDATE: 2026-01-01\nTOTAL: 105.00\nVAT: 5.00")
        pdf.save("dummy.pdf")
        pdf.close()

        # Upload file
        upload_url = "http://127.0.0.1:8000/api/v1/documents/upload"
        with open("dummy.pdf", "rb") as f:
            files = {"file": ("dummy.pdf", f, "application/pdf")}
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(upload_url, files=files, headers=headers, timeout=None)
            print("Upload response:", resp.status_code, resp.text)

if __name__ == "__main__":
    asyncio.run(main())
