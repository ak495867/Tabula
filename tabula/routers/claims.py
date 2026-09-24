"""Claims HTML routes."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from tabula.database import get_db
from tabula.models import (
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceKind,
    Outcome,
    OutcomeStatus,
    Revision,
)
from tabula.utils import (
    context,
    get_claim_or_404,
    get_sources,
    parse_date,
    templates,
)

router = APIRouter()


@router.get("", response_class=HTMLResponse)
def claims_index(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    status_filter: str = "",
) -> HTMLResponse:
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
    records = db.scalars(statement).all()
    return templates.TemplateResponse(
        request=request,
        name="claims.html",
        context=context(
            request,
            claims=records,
            query=q,
            status_filter=status_filter,
            statuses=list(ClaimStatus),
        ),
    )


@router.get("/new", response_class=HTMLResponse)
def claim_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="claim_form.html",
        context=context(
            request, claim=None, form_action="/claims", page_title="New claim"
        ),
    )


@router.post("")
def claim_create(
    db: Session = Depends(get_db),
    company: str = Form(),
    title: str = Form(),
    statement: str = Form(),
    status_value: str = Form("open"),
    confidence: int = Form(50),
    owner: str = Form(""),
    first_seen_at: str = Form(""),
) -> RedirectResponse:
    claim = Claim(
        company=company.strip(),
        title=title.strip(),
        statement=statement.strip(),
        status=ClaimStatus(status_value),
        confidence=max(0, min(confidence, 100)),
        owner=owner.strip(),
        first_seen_at=parse_date(first_seen_at),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return RedirectResponse(
        url=f"/claims/{claim.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{claim_id}", response_class=HTMLResponse)
def claim_detail(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    claim = get_claim_or_404(db, claim_id)
    return templates.TemplateResponse(
        request=request,
        name="claim_detail.html",
        context=context(
            request,
            claim=claim,
            sources=get_sources(db),
            evidence_kinds=list(EvidenceKind),
            outcome_statuses=list(OutcomeStatus),
        ),
    )


@router.get("/{claim_id}/edit", response_class=HTMLResponse)
def claim_edit(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    claim = get_claim_or_404(db, claim_id)
    return templates.TemplateResponse(
        request=request,
        name="claim_form.html",
        context=context(
            request,
            claim=claim,
            form_action=f"/claims/{claim.id}/edit",
            page_title="Edit claim",
        ),
    )


@router.post("/{claim_id}/edit")
def claim_update(
    claim_id: int,
    db: Session = Depends(get_db),
    company: str = Form(),
    title: str = Form(),
    statement: str = Form(),
    status_value: str = Form("open"),
    confidence: int = Form(50),
    owner: str = Form(""),
    first_seen_at: str = Form(""),
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    claim.company = company.strip()
    claim.title = title.strip()
    claim.statement = statement.strip()
    claim.status = ClaimStatus(status_value)
    claim.confidence = max(0, min(confidence, 100))
    claim.owner = owner.strip()
    claim.first_seen_at = parse_date(first_seen_at)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/delete")
def claim_delete(
    claim_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    db.delete(claim)
    db.commit()
    return RedirectResponse(
        url="/claims", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/evidence")
def evidence_create(
    claim_id: int,
    db: Session = Depends(get_db),
    label: str = Form(),
    kind: str = Form("excerpt"),
    excerpt: str = Form(""),
    interpretation: str = Form(""),
    source_id: int | None = Form(None),
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    evidence = Evidence(
        claim_id=claim.id,
        label=label.strip(),
        kind=EvidenceKind(kind),
        excerpt=excerpt.strip(),
        interpretation=interpretation.strip(),
        source_id=source_id or None,
    )
    db.add(evidence)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim.id}#evidence", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/evidence/{evidence_id}/delete")
def evidence_delete(
    claim_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None or evidence.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(evidence)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim_id}#evidence", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/revisions")
def revision_create(
    claim_id: int,
    db: Session = Depends(get_db),
    revised_statement: str = Form(),
    rationale: str = Form(""),
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    revision = Revision(
        claim_id=claim.id,
        previous_statement=claim.statement,
        revised_statement=revised_statement.strip(),
        rationale=rationale.strip(),
    )
    claim.statement = revised_statement.strip()
    db.add(revision)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim.id}#revisions", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/revision/{revision_id}/delete")
def revision_delete(
    claim_id: int,
    revision_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    revision = db.get(Revision, revision_id)
    if revision is None or revision.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    db.delete(revision)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim_id}#revisions", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/outcomes")
def outcome_create(
    claim_id: int,
    db: Session = Depends(get_db),
    observed_at: str = Form(),
    outcome_status: str = Form("pending"),
    summary: str = Form(""),
    source_id: int | None = Form(None),
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    outcome = Outcome(
        claim_id=claim.id,
        observed_at=parse_date(observed_at) or datetime.now().replace(tzinfo=None),
        status=OutcomeStatus(outcome_status),
        summary=summary.strip(),
        source_id=source_id or None,
    )
    db.add(outcome)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim.id}#outcomes", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{claim_id}/outcome/{outcome_id}/delete")
def outcome_delete(
    claim_id: int,
    outcome_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    outcome = db.get(Outcome, outcome_id)
    if outcome is None or outcome.claim_id != claim_id:
        raise HTTPException(status_code=404, detail="Outcome not found")
    db.delete(outcome)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim_id}#outcomes", status_code=status.HTTP_303_SEE_OTHER
    )