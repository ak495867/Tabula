"""JSON API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from tabula.database import get_db
from tabula.models import (
    Claim,
    ClaimStatus,
)
from tabula.schemas import ClaimPayload
from tabula.utils import get_claim_or_404

router = APIRouter()


@router.get("/claims")
def api_claims(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    status_filter: str = "",
) -> dict[str, object]:
    statement = select(Claim).order_by(Claim.updated_at.desc(), Claim.id.desc())
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Claim.company.ilike(pattern),
                Claim.title.ilike(pattern),
                Claim.statement.ilike(pattern),
            )
        )
    if status_filter in {item.value for item in ClaimStatus}:
        statement = statement.where(Claim.status == ClaimStatus(status_filter))

    total = db.scalar(select(1).select_from(statement.subquery())) or 0
    offset = (page - 1) * page_size
    records = db.scalars(statement.offset(offset).limit(page_size)).all()
    return {
        "items": [
            {
                "id": claim.id,
                "company": claim.company,
                "title": claim.title,
                "statement": claim.statement,
                "status": claim.status.value,
                "confidence": claim.confidence,
                "owner": claim.owner,
                "evidence_count": len(claim.evidence),
                "outcome_count": len(claim.outcomes),
            }
            for claim in records
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("/claims", status_code=201)
def api_claim_create(
    payload: ClaimPayload, db: Session = Depends(get_db)
) -> dict[str, object]:
    claim = Claim(
        company=payload.company.strip(),
        title=payload.title.strip(),
        statement=payload.statement.strip(),
        status=payload.status,
        confidence=payload.confidence,
        owner=payload.owner.strip(),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {
        "id": claim.id,
        "company": claim.company,
        "title": claim.title,
        "statement": claim.statement,
        "status": claim.status.value,
        "confidence": claim.confidence,
        "owner": claim.owner,
    }


@router.get("/claims/{claim_id}")
def api_claim_detail(
    claim_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    claim = get_claim_or_404(db, claim_id)
    return {
        "id": claim.id,
        "company": claim.company,
        "title": claim.title,
        "statement": claim.statement,
        "status": claim.status.value,
        "confidence": claim.confidence,
        "owner": claim.owner,
        "first_seen_at": claim.first_seen_at.isoformat() if claim.first_seen_at else None,
        "evidence": [
            {
                "id": item.id,
                "label": item.label,
                "kind": item.kind.value,
                "excerpt": item.excerpt,
                "interpretation": item.interpretation,
                "source_id": item.source_id,
            }
            for item in claim.evidence
        ],
        "outcomes": [
            {
                "id": item.id,
                "observed_at": item.observed_at.isoformat(),
                "status": item.status.value,
                "summary": item.summary,
                "source_id": item.source_id,
            }
            for item in claim.outcomes
        ],
    }