"""Production-readiness guard tests for engine-recon.

Mirrors the engine-fraud ``test_prod_guard.py`` pattern: in prod (DEV_MODE
unset) the service must refuse to boot when DB_URL is missing or in-memory,
or when Kafka is not enabled with brokers configured.
"""

from __future__ import annotations

from typing import Any

import pytest

from reconciliation.app import create_app
from reconciliation.config import Settings


async def _run_guard(app: Any) -> None:
    for handler in app.router.on_startup:
        name = getattr(handler, "__name__", "")
        if name == "_enforce_prod_requirements":
            await handler()
            return
    raise AssertionError("_enforce_prod_requirements startup hook not registered")


def test_db_url_defaults_to_in_memory_only_in_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_MODE", "1")
    monkeypatch.delenv("DB_URL", raising=False)
    s = Settings()
    assert s.db_url == "sqlite+aiosqlite:///:memory:"


def test_db_url_defaults_to_empty_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.delenv("DB_URL", raising=False)
    s = Settings()
    assert s.db_url == ""


def test_enable_kafka_defaults_true_when_brokers_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLE_KAFKA", raising=False)
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    s = Settings()
    assert s.enable_kafka is True


def test_enable_kafka_defaults_false_when_no_brokers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLE_KAFKA", raising=False)
    monkeypatch.delenv("KAFKA_BROKERS", raising=False)
    s = Settings()
    assert s.enable_kafka is False


def test_enable_kafka_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    monkeypatch.setenv("ENABLE_KAFKA", "false")
    s = Settings()
    assert s.enable_kafka is False


@pytest.mark.asyncio
async def test_prod_guard_dev_mode_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_MODE", "1")
    app = create_app()
    await _run_guard(app)


@pytest.mark.asyncio
async def test_prod_guard_missing_db_url_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.delenv("KAFKA_BROKERS", raising=False)
    monkeypatch.delenv("ENABLE_KAFKA", raising=False)
    from reconciliation.config import reset_settings

    reset_settings()
    app = create_app()
    with pytest.raises(SystemExit):
        await _run_guard(app)


@pytest.mark.asyncio
async def test_prod_guard_in_memory_db_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.setenv("DB_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    monkeypatch.setenv("ENABLE_KAFKA", "true")
    from reconciliation.config import reset_settings

    reset_settings()
    app = create_app()
    with pytest.raises(SystemExit):
        await _run_guard(app)


@pytest.mark.asyncio
async def test_prod_guard_kafka_disabled_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.setenv("DB_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/recon")
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    monkeypatch.setenv("ENABLE_KAFKA", "false")
    from reconciliation.config import reset_settings

    reset_settings()
    app = create_app()
    with pytest.raises(SystemExit):
        await _run_guard(app)


@pytest.mark.asyncio
async def test_prod_guard_all_envs_set_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.setenv("DB_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/recon")
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    monkeypatch.setenv("ENABLE_KAFKA", "true")
    from reconciliation.config import reset_settings

    reset_settings()
    app = create_app()
    await _run_guard(app)
