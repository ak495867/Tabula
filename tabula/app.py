from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from tabula.database import get_db, init_db
from tabula.models import (
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceKind,
    Outcome,
    OutcomeStatus,
    Revision,
    Source,
)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tabula", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def context(request: Request, **values: object) -> dict[str, object]:
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


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    claims = db.scalars(
        select(Claim).order_by(Claim.updated_at.desc(), Claim.id.desc())
    ).all()
    counts = {
        status.value: sum(1 for claim in claims if claim.status == status)
        for status in ClaimStatus
    }
    evidence_count = db.scalar(select(func.count(Evidence.id))) or 0
    source_count = db.scalar(select(func.count(Source.id))) or 0
    outcome_count = db.scalar(select(func.count(Outcome.id))) or 0
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context(
            request,
            claims=claims,
            counts=counts,
            evidence_count=evidence_count,
            source_count=source_count,
            outcome_count=outcome_count,
        ),
    )


@app.get("/claims", response_class=HTMLResponse)
def claims_index(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
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


@app.get("/claims/new", response_class=HTMLResponse)
def claim_new(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="claim_form.html",
        context=context(
            request, claim=None, form_action="/claims", page_title="New claim"
        ),
    )


@app.post("/claims")
def claim_create(
    db: Annotated[Session, Depends(get_db)],
    company: Annotated[str, Form()],
    title: Annotated[str, Form()],
    statement: Annotated[str, Form()],
    status_value: Annotated[str, Form()] = "open",
    confidence: Annotated[int, Form()] = 50,
    owner: Annotated[str, Form()] = "",
    first_seen_at: Annotated[str, Form()] = "",
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


@app.get("/claims/{claim_id}", response_class=HTMLResponse)
def claim_detail(
    request: Request, claim_id: int, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    claim = get_claim_or_404(db, claim_id)
    sources = db.scalars(select(Source).order_by(Source.title.asc())).all()
    return templates.TemplateResponse(
        request=request,
        name="claim_detail.html",
        context=context(
            request,
            claim=claim,
            sources=sources,
            evidence_kinds=list(EvidenceKind),
            outcome_statuses=list(OutcomeStatus),
        ),
    )


@app.get("/claims/{claim_id}/edit", response_class=HTMLResponse)
def claim_edit(
    request: Request, claim_id: int, db: Annotated[Session, Depends(get_db)]
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


@app.post("/claims/{claim_id}/edit")
def claim_update(
    claim_id: int,
    db: Annotated[Session, Depends(get_db)],
    company: Annotated[str, Form()],
    title: Annotated[str, Form()],
    statement: Annotated[str, Form()],
    status_value: Annotated[str, Form()] = "open",
    confidence: Annotated[int, Form()] = 50,
    owner: Annotated[str, Form()] = "",
    first_seen_at: Annotated[str, Form()] = "",
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


@app.post("/claims/{claim_id}/evidence")
def evidence_create(
    claim_id: int,
    db: Annotated[Session, Depends(get_db)],
    label: Annotated[str, Form()],
    kind: Annotated[str, Form()] = "excerpt",
    excerpt: Annotated[str, Form()] = "",
    interpretation: Annotated[str, Form()] = "",
    source_id: Annotated[int | None, Form()] = None,
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


@app.post("/claims/{claim_id}/revisions")
def revision_create(
    claim_id: int,
    db: Annotated[Session, Depends(get_db)],
    revised_statement: Annotated[str, Form()],
    rationale: Annotated[str, Form()] = "",
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


@app.post("/claims/{claim_id}/outcomes")
def outcome_create(
    claim_id: int,
    db: Annotated[Session, Depends(get_db)],
    observed_at: Annotated[str, Form()],
    outcome_status: Annotated[str, Form()] = "pending",
    summary: Annotated[str, Form()] = "",
    source_id: Annotated[int | None, Form()] = None,
) -> RedirectResponse:
    claim = get_claim_or_404(db, claim_id)
    outcome = Outcome(
        claim_id=claim.id,
        observed_at=parse_date(observed_at) or datetime.now(UTC).replace(tzinfo=None),
        status=OutcomeStatus(outcome_status),
        summary=summary.strip(),
        source_id=source_id or None,
    )
    db.add(outcome)
    db.commit()
    return RedirectResponse(
        url=f"/claims/{claim.id}#outcomes", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/sources", response_class=HTMLResponse)
def sources_index(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    sources = db.scalars(
        select(Source).order_by(Source.created_at.desc(), Source.id.desc())
    ).all()
    return templates.TemplateResponse(
        request=request, name="sources.html", context=context(request, sources=sources)
    )


@app.post("/sources")
def source_create(
    db: Annotated[Session, Depends(get_db)],
    title: Annotated[str, Form()],
    publisher: Annotated[str, Form()] = "",
    source_type: Annotated[str, Form()] = "Other",
    url: Annotated[str, Form()] = "",
    published_at: Annotated[str, Form()] = "",
) -> RedirectResponse:
    source = Source(
        title=title.strip(),
        publisher=publisher.strip(),
        source_type=source_type.strip() or "Other",
        url=url.strip(),
        published_at=parse_date(published_at),
    )
    db.add(source)
    db.commit()
    return RedirectResponse(url="/sources", status_code=status.HTTP_303_SEE_OTHER)


class ClaimPayload(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1)
    status: ClaimStatus = ClaimStatus.open
    confidence: int = Field(default=50, ge=0, le=100)
    owner: str = ""


@app.get("/api/claims")
def api_claims(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, object]]:
    records = db.scalars(
        select(Claim).order_by(Claim.updated_at.desc(), Claim.id.desc())
    ).all()
    return [
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
    ]


@app.post("/api/claims", status_code=201)
def api_claim_create(
    payload: ClaimPayload, db: Annotated[Session, Depends(get_db)]
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
