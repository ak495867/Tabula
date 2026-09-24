"""Pydantic schemas and shared helpers."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from tabula.models import ClaimStatus, EvidenceKind, OutcomeStatus


class ClaimPayload(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1)
    status: ClaimStatus = ClaimStatus.open
    confidence: int = Field(default=50, ge=0, le=100)
    owner: str = ""


class ClaimUpdate(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1)
    status_value: str = "open"
    confidence: int = Field(default=50, ge=0, le=100)
    owner: str = ""
    first_seen_at: str = ""


class EvidenceCreate(BaseModel):
    claim_id: int
    label: str = Field(min_length=1, max_length=180)
    kind: EvidenceKind = EvidenceKind.excerpt
    excerpt: str = ""
    interpretation: str = ""
    source_id: int | None = None


class EvidenceUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    kind: EvidenceKind
    excerpt: str = ""
    interpretation: str = ""
    source_id: int | None = None


class RevisionCreate(BaseModel):
    claim_id: int
    revised_statement: str = Field(min_length=1)
    rationale: str = ""


class RevisionUpdate(BaseModel):
    revised_statement: str = Field(min_length=1)
    rationale: str = ""


class OutcomeCreate(BaseModel):
    claim_id: int
    observed_at: str = ""
    status_value: OutcomeStatus = OutcomeStatus.pending
    summary: str = ""
    source_id: int | None = None


class OutcomeUpdate(BaseModel):
    observed_at: str = ""
    status_value: OutcomeStatus
    summary: str = ""
    source_id: int | None = None


class SourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    publisher: str = ""
    source_type: str = "Other"
    url: str = ""
    published_at: str = ""


class SourceUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    publisher: str = ""
    source_type: str = "Other"
    url: str = ""
    published_at: str = ""


PageQuery = Annotated[int, Field(default=1, ge=1)]
PageSize = Annotated[int, Field(default=20, ge=1, le=100)]