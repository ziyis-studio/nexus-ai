from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Priority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class TicketStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class TicketCreate(StrictModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    customer_name: str | None = Field(default=None, max_length=150)
    customer_email: EmailStr | None = Field(default=None, max_length=254)
    external_reference: str | None = Field(default=None, max_length=200)


class TicketPatch(StrictModel):
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    status: TicketStatus | None = None
    priority: Priority | None = None
    customer_name: str | None = Field(default=None, max_length=150)
    customer_email: EmailStr | None = Field(default=None, max_length=254)
    external_reference: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None
            for name in self.model_fields_set & {"subject", "description", "status", "priority"}
        ):
            raise ValueError("Provide at least one valid update; required fields cannot be null.")
        return self


class Ticket(TicketCreate):
    id: UUID
    tenant_id: UUID
    created_by: UUID
    status: TicketStatus
    priority: Priority
    created_at: datetime
    updated_at: datetime


DocumentType = Literal["faq", "policy", "product_information", "general_reference"]


class KnowledgeCreate(StrictModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=10, max_length=50000)
    document_type: DocumentType = "general_reference"
    is_active: bool = True


class KnowledgePatch(StrictModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    content: str | None = Field(default=None, min_length=10, max_length=50000)
    document_type: DocumentType | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, k) is None for k in self.model_fields_set
        ):
            raise ValueError("Provide a non-null document update.")
        return self


class Knowledge(KnowledgeCreate):
    id: UUID
    tenant_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AIOutput(StrictModel):
    category: Literal["billing", "delivery", "technical", "account", "general", "other"]
    suggested_priority: Priority
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str = Field(min_length=1, max_length=2000)
    suggested_reply: str = Field(min_length=1, max_length=6000)
    needs_human_review: bool
    reasoning_summary: str = Field(min_length=1, max_length=1000)
    source_document_ids: list[UUID] = Field(max_length=5)

    @field_validator("needs_human_review", mode="before")
    @classmethod
    def strict_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Expected a boolean")
        return value


class AIResult(AIOutput):
    id: UUID
    tenant_id: UUID
    run_id: UUID
    review_status: Literal["pending", "approved", "rejected"]
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class Run(BaseModel):
    id: UUID
    tenant_id: UUID
    ticket_id: UUID
    initiated_by: UUID
    status: Literal["queued", "processing", "succeeded", "failed"]
    model_id: str
    attempt_count: int
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AnalysisAccepted(StrictModel):
    run_id: UUID
    status: str
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None


class Tenant(StrictModel):
    id: UUID
    name: str
    slug: str
    role: Literal["admin", "agent", "viewer"]


class Principal(StrictModel):
    id: UUID
    email: str | None = None


class Member(BaseModel):
    user_id: UUID
    role: str
    is_active: bool
    created_at: datetime


class Audit(BaseModel):
    id: UUID
    tenant_id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    metadata: dict[str, Any]
    created_at: datetime


class ErrorBody(StrictModel):
    code: str
    message: str
    request_id: UUID


class ErrorResponse(StrictModel):
    error: ErrorBody
