import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_register_and_me():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/auth/register", json={
            "email": "u1@example.com",
            "username": "u1user",
            "password": "supersecret1"
        })
        assert r.status_code == 200
        token = r.json()["access_token"]

        r2 = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["email"] == "u1@example.com"
