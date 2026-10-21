import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.v1.auth import router as auth_router
from src.api.v1.roles import router as roles_router
from src.api.v1.users import router as users_router
from src.core.security import create_access_token, verify_password
from src.db.session import get_db
from src.models.entities import Role, Tenant, User, UserRole


class AsyncSessionAdapter:
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, entity):
        self.session.add(entity)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


class UserTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        for table in (Tenant.__table__, User.__table__, Role.__table__, UserRole.__table__):
            table.create(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session.add_all([
            Tenant(id="tenant_a", name="A", code="a"),
            Tenant(id="tenant_b", name="B", code="b"),
            User(id="admin_a", tenant_id="tenant_a", email="admin@example.com",
                 name="Admin", hashed_password="unused", is_admin=True),
            User(id="ordinary_a", tenant_id="tenant_a", email="ordinary@example.com",
                 name="Ordinary", hashed_password="unused", is_admin=False),
            User(id="ordinary_b", tenant_id="tenant_b", email="other@example.com",
                 name="Other", hashed_password="unused", is_admin=False),
            Role(id="role_a", tenant_id="tenant_a", code="reader", name="Reader",
                 permissions=["agents:read"]),
            Role(id="role_a_two", tenant_id="tenant_a", code="writer", name="Writer",
                 permissions=["agents:write"]),
            Role(id="role_b", tenant_id="tenant_b", code="reader", name="Reader"),
        ])
        self.session.commit()
        self.db = AsyncSessionAdapter(self.session)
        app = FastAPI()
        app.include_router(roles_router, prefix="/api/v1/roles", tags=["Roles & Permissions"])
        app.include_router(auth_router, prefix="/api/v1/auth")
        app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])

        async def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {create_access_token('admin_a')}"}
        self.payload = {
            "email": "new@example.com", "name": "New user",
            "password": "test123456",
        }

    def tearDown(self):
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def create_user(self, payload=None, headers=None):
        return self.client.post(
            "/api/v1/users", json=self.payload if payload is None else payload,
            headers=self.headers if headers is None else headers,
        )

    def assign_role(self, user_id, role_id="role_a"):
        return self.client.post("/api/v1/roles/assign", headers=self.headers, json={
            "user_id": user_id, "role_id": role_id,
        })

    def test_creation_login_and_permissions(self):
        response = self.create_user()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        new_user = self.session.get(User, data["user_id"])
        self.assertFalse(new_user.is_admin)
        self.assertEqual(new_user.tenant_id, "tenant_a")
        self.assertTrue(verify_password(self.payload["password"], new_user.hashed_password))
        self.assertNotIn("password", data)
        self.assertEqual(data["role_ids"], [])
        self.assertEqual(self.assign_role(new_user.id).status_code, 200)
        link = self.session.execute(select(UserRole)).scalar_one()
        self.assertEqual((link.user_id, link.role_id), (new_user.id, "role_a"))
        login_response = self.client.post("/api/v1/auth/login", json={
            "email": self.payload["email"], "password": self.payload["password"],
        })
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["data"]["access_token"]
        permissions = self.client.get(
            "/api/v1/roles/me/permissions", headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(permissions.json()["data"]["permissions"], ["agents:read"])

    def test_reject_duplicate_email(self):
        self.assertEqual(self.create_user().status_code, 200)
        self.assertEqual(self.create_user().status_code, 409)
        self.assertEqual(len(self.session.execute(select(UserRole)).scalars().all()), 0)

    def test_reject_missing_or_other_tenant_role(self):
        user_id = self.create_user().json()["data"]["user_id"]
        for role_id in ("missing", "role_b"):
            with self.subTest(role_id=role_id):
                self.assertEqual(self.assign_role(user_id, role_id).status_code, 404)
        self.assertEqual(self.session.execute(select(UserRole)).scalars().all(), [])

    def test_require_admin(self):
        self.assertEqual(self.create_user(headers={}).status_code, 401)
        headers = {"Authorization": f"Bearer {create_access_token('ordinary_a')}"}
        self.assertEqual(self.create_user(headers=headers).status_code, 403)

    def test_validate_input(self):
        for changes in ({"email": "invalid"}, {"name": ""}, {"password": "short"}, {"password": "密" * 25}):
            with self.subTest(changes=changes):
                self.assertEqual(self.create_user({**self.payload, **changes}).status_code, 422)

    def test_create_without_role(self):
        response = self.create_user()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["role_ids"], [])

    def test_list_detail_and_pagination(self):
        user_id = self.create_user().json()["data"]["user_id"]
        self.assertEqual(self.assign_role(user_id).status_code, 200)
        response = self.client.get("/api/v1/users", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        users = response.json()["data"]
        self.assertEqual(len(users), 3)
        self.assertTrue(all(user["tenant_id"] == "tenant_a" for user in users))
        self.assertTrue(all("hashed_password" not in user for user in users))
        page = self.client.get("/api/v1/users?offset=1&limit=1", headers=self.headers)
        self.assertEqual(len(page.json()["data"]), 1)
        detail = self.client.get(f"/api/v1/users/{user_id}", headers=self.headers)
        self.assertEqual(detail.json()["data"]["role_ids"], ["role_a"])

    def test_update_password_email_preserves_roles(self):
        user_id = self.create_user().json()["data"]["user_id"]
        self.assertEqual(self.assign_role(user_id).status_code, 200)
        response = self.client.patch(f"/api/v1/users/{user_id}", headers=self.headers, json={
            "email": "changed@example.com", "name": "Changed", "password": "changed1234",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["role_ids"], ["role_a"])
        self.assertEqual(response.json()["data"]["name"], "Changed")
        login_response = self.client.post("/api/v1/auth/login", json={
            "email": "changed@example.com", "password": "changed1234",
        })
        self.assertEqual(login_response.status_code, 200)
        login_response = self.client.post("/api/v1/auth/login", json={
            "email": "changed@example.com", "password": self.payload["password"],
        })
        self.assertEqual(login_response.status_code, 401)

    def test_update_validation_and_conflict(self):
        user_id = self.create_user().json()["data"]["user_id"]
        for payload, status_code in (
            ({"email": "admin@example.com"}, 409),
            ({"role_id": "role_a"}, 422),
            ({"name": None}, 422),
            ({"is_active": None}, 422),
            ({"password": "short"}, 422),
            ({"is_admin": True}, 422),
        ):
            with self.subTest(payload=payload):
                response = self.client.patch(f"/api/v1/users/{user_id}", headers=self.headers, json=payload)
                self.assertEqual(response.status_code, status_code)
        target_user = self.session.get(User, user_id)
        self.assertEqual(target_user.email, self.payload["email"])

    def test_disable_user_invalidates_token(self):
        user_id = self.create_user().json()["data"]["user_id"]
        response = self.client.patch(f"/api/v1/users/{user_id}", headers=self.headers, json={"is_active": False})
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/api/v1/auth/me", headers={"Authorization": f"Bearer {create_access_token(user_id)}"})
        self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/v1/auth/login", json={
            "email": self.payload["email"], "password": self.payload["password"],
        })
        self.assertEqual(response.status_code, 401)

    def test_delete_user_and_bindings(self):
        user_id = self.create_user().json()["data"]["user_id"]
        self.assertEqual(self.assign_role(user_id).status_code, 200)
        response = self.client.delete(f"/api/v1/users/{user_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.session.get(User, user_id))
        self.assertEqual(self.session.execute(select(UserRole)).scalars().all(), [])
        self.assertEqual(self.client.get(f"/api/v1/users/{user_id}", headers=self.headers).status_code, 404)

    def test_all_operations_require_admin_and_same_tenant(self):
        requests = (
            ("get", "/api/v1/users", None),
            ("get", "/api/v1/users/ordinary_b", None),
            ("patch", "/api/v1/users/ordinary_b", {"name": "Changed"}),
            ("delete", "/api/v1/users/ordinary_b", None),
        )
        ordinary_headers = {"Authorization": f"Bearer {create_access_token('ordinary_a')}"}
        for method, path, payload in requests:
            for headers, status_code in (({}, 401), (ordinary_headers, 403)):
                response = self.client.request(method, path, headers=headers, json=payload)
                self.assertEqual(response.status_code, status_code)
            if path != "/api/v1/users":
                response = self.client.request(method, path, headers=self.headers, json=payload)
                self.assertEqual(response.status_code, 404)

    def test_prevent_self_deletion_or_disabling(self):
        response = self.client.delete("/api/v1/users/admin_a", headers=self.headers)
        self.assertEqual(response.status_code, 400)
        response = self.client.patch("/api/v1/users/admin_a", headers=self.headers, json={"is_active": False})
        self.assertEqual(response.status_code, 400)

    def test_update_rollback(self):
        user_id = self.create_user().json()["data"]["user_id"]
        self.assertEqual(self.assign_role(user_id).status_code, 200)
        with patch.object(self.db, "commit", side_effect=IntegrityError("update", {}, Exception("failed"))):
            with self.assertRaises(IntegrityError):
                self.client.patch(f"/api/v1/users/{user_id}", headers=self.headers, json={"name": "Changed"})
        self.assertEqual(self.session.get(User, user_id).name, self.payload["name"])
        self.assertEqual(self.session.execute(select(UserRole)).scalar_one().role_id, "role_a")

    def test_delete_rollback(self):
        user_id = self.create_user().json()["data"]["user_id"]
        self.assertEqual(self.assign_role(user_id).status_code, 200)
        with patch.object(self.db, "commit", side_effect=IntegrityError("delete", {}, Exception("failed"))):
            with self.assertRaises(IntegrityError):
                self.client.delete(f"/api/v1/users/{user_id}", headers=self.headers)
        self.assertIsNotNone(self.session.get(User, user_id))
        self.assertEqual(self.session.execute(select(UserRole)).scalar_one().user_id, user_id)

    def test_openapi_users_group(self):
        from src.main import app

        schema = app.openapi()
        paths = schema["paths"]
        for model_name in ("UserCreateRequest", "UserUpdateRequest"):
            self.assertNotIn("role_id", schema["components"]["schemas"][model_name]["properties"])
        self.assertNotIn("/api/v1/roles/users", paths)
        for path, methods in (
            ("/api/v1/users", ("post", "get")),
            ("/api/v1/users/{user_id}", ("get", "patch", "delete")),
        ):
            for method in methods:
                self.assertEqual(paths[path][method]["tags"], ["Users"])

    def test_create_rejects_role_id(self):
        response = self.create_user({**self.payload, "role_id": "role_a"})
        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.session.execute(select(User).where(User.email == self.payload["email"])).scalar_one_or_none())

    def test_rollback_when_user_creation_fails(self):
        with patch.object(self.db, "commit", side_effect=IntegrityError("insert", {}, Exception("creation failed"))):
            with self.assertRaises(IntegrityError):
                self.create_user()
        self.assertIsNone(self.session.execute(select(User).where(User.email == self.payload["email"])).scalar_one_or_none())
        self.assertEqual(self.session.execute(select(UserRole)).scalars().all(), [])


if __name__ == "__main__":
    unittest.main()
