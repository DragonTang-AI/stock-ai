"""
tests/api/test_auth.py — 认证 API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
class TestAuth:
    """POST /api/v1/auth/* 的测试"""

    async def test_register_success(self, client: AsyncClient) -> None:
        """注册成功"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "securepass123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "hashed_password" not in data  # 不暴露密码

    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User) -> None:
        """重复用户名"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,
                "email": "another@example.com",
                "password": "pass123456",
            },
        )
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient, test_user: User) -> None:
        """登录成功"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User) -> None:
        """密码错误"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        """用户不存在"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost", "password": "password"},
        )
        assert response.status_code == 401

    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """获取当前用户（已认证）"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    async def test_get_me_unauthenticated(self, client: AsyncClient) -> None:
        """获取当前用户（未认证）"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_refresh_token(self, client: AsyncClient, test_user: User) -> None:
        """刷新 Token"""
        # 先登录获取 refresh_token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # 刷新
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_invalid(self, client: AsyncClient) -> None:
        """无效 refresh_token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "fake_token"},
        )
        assert response.status_code == 401

    async def test_logout(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """登出（JWT 无状态，前端删 Token 即可，这里返回成功即可）"""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
