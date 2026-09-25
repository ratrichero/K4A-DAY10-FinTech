from __future__ import annotations

from pathlib import Path
import pytest

from core.config import Settings, load_settings


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def project_root(settings: Settings) -> Path:
    return settings.paths.project_dir
