"""Tabula FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tabula.database import get_db, init_db
from tabula.models import Claim, ClaimStatus, Evidence, Outcome, Source
from tabula.utils import context, templates
from tabula.routers.claims import router as claims_router
from tabula.routers.sources import router as sources_router
from tabula.routers.api import router as api_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tabula", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(claims_router, prefix="/claims", tags=["claims"])
app.include_router(sources_router, prefix="/sources", tags=["sources"])
app.include_router(api_router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request, db: Session = Depends(get_db)
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