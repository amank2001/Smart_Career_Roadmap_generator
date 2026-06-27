"""Lightweight internal event bus using asyncio callbacks.

This module provides a simple publish/subscribe event system for decoupling
domain events (e.g., plan completion, task completion) from their side effects
(e.g., skill proficiency updates, notifications).

Usage:
    from app.core.events import event_bus, PlanCompleted, TaskCompleted

    # Subscribe a handler
    @event_bus.subscribe(PlanCompleted)
    async def handle_plan_completed(event: PlanCompleted):
        ...

    # Emit an event
    await event_bus.emit(PlanCompleted(user_id=..., plan_id=...))
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Type
from uuid import UUID

logger = logging.getLogger(__name__)


# ── Event Definitions ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    pass


@dataclass(frozen=True)
class PlanCompleted(DomainEvent):
    """Emitted when all tasks in a weekly plan are marked complete."""
    user_id: UUID
    plan_id: UUID


@dataclass(frozen=True)
class TaskCompleted(DomainEvent):
    """Emitted when a single task within a weekly plan is marked complete."""
    user_id: UUID
    plan_id: UUID
    task_id: UUID
    skill_name: str


@dataclass(frozen=True)
class RoadmapCompleted(DomainEvent):
    """Emitted when the final plan in a roadmap is completed."""
    user_id: UUID
    roadmap_id: UUID


# ── Event Bus Implementation ──────────────────────────────────────────────────

# Type alias for async event handlers
EventHandler = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    """A simple async event bus that dispatches domain events to registered handlers.

    Handlers are registered per event type and called asynchronously when an
    event of that type is emitted. Errors in handlers are logged but do not
    prevent other handlers from running.
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[EventHandler]] = {}

    def subscribe(self, event_type: Type[DomainEvent]) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an async handler for a specific event type.

        Example:
            @event_bus.subscribe(PlanCompleted)
            async def on_plan_completed(event: PlanCompleted):
                ...
        """
        def decorator(handler: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            return handler
        return decorator

    def register(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """Imperatively register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    async def emit(self, event: DomainEvent) -> None:
        """Emit an event, invoking all registered handlers for its type.

        Handlers are called concurrently via asyncio.gather. Errors in
        individual handlers are logged but do not propagate or prevent
        other handlers from executing.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug("No handlers registered for event: %s", event_type.__name__)
            return

        logger.info("Emitting event %s to %d handler(s)", event_type.__name__, len(handlers))

        results = await asyncio.gather(
            *(self._safe_call(handler, event) for handler in handlers),
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Handler %s raised an exception for event %s: %s",
                    handlers[i].__name__,
                    event_type.__name__,
                    result,
                )

    @staticmethod
    async def _safe_call(handler: EventHandler, event: DomainEvent) -> None:
        """Invoke a handler, catching and re-raising exceptions for gather."""
        try:
            await handler(event)
        except Exception as exc:
            logger.exception(
                "Error in event handler %s: %s", handler.__name__, exc
            )
            raise

    def clear(self) -> None:
        """Remove all registered handlers. Useful for testing."""
        self._handlers.clear()


# ── Singleton event bus instance ──────────────────────────────────────────────

event_bus = EventBus()
