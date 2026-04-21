from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.auth import AuthService, LoginService
from app.models.auth import User, UserRole


def test_password_hash_and_verify() -> None:
    password = "securepass123"
    password_hash = AuthService.hash_password(password)

    assert password_hash != password
    assert AuthService.verify_password(password, password_hash)
    assert not AuthService.verify_password("badpass", password_hash)


def test_jwt_encode_decode_round_trip() -> None:
    user = User(id=uuid.uuid4(), username="unit-user", password_hash="x", role=UserRole.CASHIER)
    token = AuthService.create_access_token(user.id, user.role)
    payload = AuthService.decode_access_token(token)

    assert payload["sub"] == str(user.id)
    assert payload["role"] == UserRole.CASHIER.value


def test_lockout_after_max_attempts() -> None:
    user = User(username="lock-user", password_hash="x", role=UserRole.CASHIER)
    user.failed_login_count = 0
    user.locked_until = None

    for _ in range(5):
        LoginService.register_failed_attempt(user)

    assert user.failed_login_count == 5
    assert user.locked_until is not None
    assert LoginService.is_locked(user)


def test_lock_remaining_seconds_non_negative() -> None:
    user = User(username="remain-user", password_hash="x", role=UserRole.CASHIER)
    user.locked_until = datetime.now(UTC) + timedelta(seconds=10)

    remaining = LoginService.lock_remaining_seconds(user)

    assert remaining >= 0
