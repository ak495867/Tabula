from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tabula.database import Base


class ClaimStatus(str, Enum):
    open = "open"
    supported = "supported"
    challenged = "challenged"
    resolved = "resolved"


class EvidenceKind(str, Enum):
    source = "source"
    excerpt = "excerpt"
    metric = "metric"
    artifact = "artifact"


class OutcomeStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    mixed = "mixed"
    contradicted = "contradicted"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    publisher: Mapped[str] = mapped_column(String(160), default="")
    source_type: Mapped[str] = mapped_column(String(80), default="Other")
    url: Mapped[str] = mapped_column(String(1000), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    evidence: Mapped[list[Evidence]] = relationship(back_populates="source")


class Claim(Base):
    __tablename__ = "claims"

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="confidence_range"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(240))
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[ClaimStatus] = mapped_column(
        SQLEnum(ClaimStatus), default=ClaimStatus.open, index=True
    )
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    owner: Mapped[str] = mapped_column(String(120), default="")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), index=True
    )
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[Revision]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="Revision.created_at",
    )
    outcomes: Mapped[list[Outcome]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="Outcome.observed_at",
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[EvidenceKind] = mapped_column(
        SQLEnum(EvidenceKind), default=EvidenceKind.excerpt
    )
    label: Mapped[str] = mapped_column(String(180))
    excerpt: Mapped[str] = mapped_column(Text, default="")
    interpretation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    claim: Mapped[Claim] = relationship(back_populates="evidence")
    source: Mapped[Source | None] = relationship(back_populates="evidence")


class Revision(Base):
    __tablename__ = "revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    previous_statement: Mapped[str] = mapped_column(Text, default="")
    revised_statement: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    claim: Mapped[Claim] = relationship(back_populates="revisions")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    status: Mapped[OutcomeStatus] = mapped_column(
        SQLEnum(OutcomeStatus), default=OutcomeStatus.pending
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    claim: Mapped[Claim] = relationship(back_populates="outcomes")