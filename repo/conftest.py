from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthService
from app.db.session import Base, get_db
from app.main import app
from app.models.auth import User, UserRole


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        future=True,
    )

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    admin = User(
        id=uuid.uuid4(),
        username="admin",
        password_hash=AuthService.hash_password("adminpass123"),
        role=UserRole.ADMIN,
    )
    cashier = User(
        id=uuid.uuid4(),
        username="cashier",
        password_hash=AuthService.hash_password("cashierpass123"),
        role=UserRole.CASHIER,
    )
    store_manager = User(
        id=uuid.uuid4(),
        username="store-manager",
        password_hash=AuthService.hash_password("storemanagerpass123"),
        role=UserRole.STORE_MANAGER,
    )
    applicant = User(
        id=uuid.uuid4(),
        username="applicant",
        password_hash=AuthService.hash_password("applicantpass123"),
        role=UserRole.APPLICANT,
    )
    reviewer = User(
        id=uuid.uuid4(),
        username="reviewer",
        password_hash=AuthService.hash_password("reviewerpass123"),
        role=UserRole.REVIEWER,
    )
    session.add_all([admin, cashier, store_manager, applicant, reviewer])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def cashier_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "cashier", "password": "cashierpass123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def store_manager_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "store-manager", "password": "storemanagerpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def applicant_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "applicant", "password": "applicantpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def reviewer_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "reviewer", "password": "reviewerpass123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
