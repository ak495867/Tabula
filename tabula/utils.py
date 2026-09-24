"""Shared utilities for Tabula."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from tabula.models import Claim, Evidence, Source

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def context(request: object, **values: object) -> dict[str, object]:
    return {"request": request, "app_name": "Tabula", **values}


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Date must use YYYY-MM-DD format"
        ) from exc


def parse_date_or_now(value: str) -> datetime:
    parsed = parse_date(value)
    if parsed is None:
        return datetime.now().replace(tzinfo=None)
    return parsed


def get_claim_or_404(db: Session, claim_id: int) -> Claim:
    statement = (
        select(Claim)
        .options(
            joinedload(Claim.evidence).joinedload(Evidence.source),
            joinedload(Claim.revisions),
            joinedload(Claim.outcomes),
        )
        .where(Claim.id == claim_id)
    )
    claim = db.execute(statement).unique().scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def get_sources(db: Session) -> Sequence[Source]:
    return db.scalars(select(Source).order_by(Source.title.asc())).all()


def get_claim_context(claim: Claim, db: Session) -> dict[str, object]:
    from tabula.models import EvidenceKind, OutcomeStatus
    return {
        "claim": claim,
        "sources": get_sources(db),
        "evidence_kinds": list(EvidenceKind),
        "outcome_statuses": list(OutcomeStatus),
    }