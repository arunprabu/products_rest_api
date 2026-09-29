"""Validated application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings. Environment variables override the safe local defaults."""

    database_path: Path
    log_level: str
    api_prefix: str = "/api/v1"

    @classmethod
    def from_environment(cls) -> Settings:
        """Create settings, rejecting invalid log levels early."""
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed_levels)}")
        return cls(
            database_path=Path(os.getenv("DATABASE_PATH", "./data/products.db")),
            log_level=log_level,
        )
