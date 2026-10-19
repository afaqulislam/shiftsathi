"""Shared enums used across models and schemas."""

from __future__ import annotations

import enum


class Role(enum.StrEnum):
    admin = "admin"
    supervisor = "supervisor"
    worker = "worker"


class DocumentStatus(enum.StrEnum):
    pending = "pending"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class Severity(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(enum.StrEnum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


class WorkOrderStatus(enum.StrEnum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(enum.StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class MessageRole(enum.StrEnum):
    user = "user"
    assistant = "assistant"


class KnowledgeSource(enum.StrEnum):
    verified_resolution = "verified_resolution"
    document = "document"
