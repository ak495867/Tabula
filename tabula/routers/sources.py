"""Sources HTML routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from tabula.database import get_db
from tabula.models import Source
from tabula.utils import context, parse_date, templates

router = APIRouter()


@router.get("", response_class=HTMLResponse)
def sources_index(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    sources = db.scalars(
        select(Source).order_by(Source.created_at.desc(), Source.id.desc())
    ).all()
    return templates.TemplateResponse(
        request=request, name="sources.html", context=context(request, sources=sources)
    )


@router.post("")
def source_create(
    db: Session = Depends(get_db),
    title: str = Form(),
    publisher: str = Form(""),
    source_type: str = Form("Other"),
    url: str = Form(""),
    published_at: str = Form(""),
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


@router.get("/{source_id}/edit", response_class=HTMLResponse)
def source_edit(
    request: Request,
    source_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return templates.TemplateResponse(
        request=request,
        name="source_form.html",
        context=context(
            request,
            source=source,
            form_action=f"/sources/{source.id}/edit",
            page_title="Edit source",
        ),
    )


@router.post("/{source_id}/edit")
def source_update(
    source_id: int,
    db: Session = Depends(get_db),
    title: str = Form(),
    publisher: str = Form(""),
    source_type: str = Form("Other"),
    url: str = Form(""),
    published_at: str = Form(""),
) -> RedirectResponse:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    source.title = title.strip()
    source.publisher = publisher.strip()
    source.source_type = source_type.strip() or "Other"
    source.url = url.strip()
    source.published_at = parse_date(published_at)
    db.commit()
    return RedirectResponse(url="/sources", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{source_id}/delete")
def source_delete(
    source_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return RedirectResponse(url="/sources", status_code=status.HTTP_303_SEE_OTHER)