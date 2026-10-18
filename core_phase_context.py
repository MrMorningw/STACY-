"""Thread-local request context used to route CORE phase events safely."""
from __future__ import annotations

from contextlib import contextmanager
from threading import local
from typing import Iterator


_MISSING = object()


class CorePhaseContext:
    """Keep execution IDs isolated when the HTTP server handles requests concurrently."""

    def __init__(self) -> None:
        self._state = local()

    def current_execution_id(self):
        return getattr(self._state, "execution_id", None)

    @contextmanager
    def bind(self, execution_id) -> Iterator[None]:
        previous = getattr(self._state, "execution_id", _MISSING)
        self._state.execution_id = execution_id
        try:
            yield
        finally:
            if previous is _MISSING:
                try:
                    del self._state.execution_id
                except AttributeError:
                    pass
            else:
                self._state.execution_id = previous
