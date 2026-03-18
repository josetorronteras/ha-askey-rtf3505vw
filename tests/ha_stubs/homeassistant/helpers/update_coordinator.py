"""Minimal stub for homeassistant.helpers.update_coordinator."""
from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator(Generic[T]):
    """Minimal stub that provides just enough for AskeyCoordinator."""

    def __init__(
        self,
        hass: Any,
        logger: logging.Logger,
        *,
        name: str,
        update_interval: Any = None,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: T | None = None
        self.config_entry: Any = None
