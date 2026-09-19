from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import CheckDefinition
from app.services.checks.registry import registered
from app.services.scoring.version_resolver import checks_effective_on

router = APIRouter(tags=["check-library"])


@router.get("/checks")
def list_checks(retailer_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(CheckDefinition).order_by(
        CheckDefinition.check_id, CheckDefinition.version)
    if retailer_id:
        stmt = stmt.where(CheckDefinition.retailer_id == retailer_id)
    return [{
        "check_id": c.check_id, "version": c.version, "name": c.name, "type": c.type,
        "critical": c.critical, "weight": float(c.weight),
        "effective_from": c.effective_from, "effective_to": c.effective_to,
        "handler": (c.config or {}).get("handler"),
    } for c in db.execute(stmt).scalars().all()]


@router.get("/checks/effective")
def effective_checks(
    retailer_id: str,
    at: datetime = Query(..., description="Call date. Resolution is by call date, not today."),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [{"check_id": c.check_id, "version": c.version, "name": c.name,
             "critical": c.critical} for c in checks_effective_on(db, retailer_id, at)]


@router.get("/checks/handlers")
def list_handlers() -> list[str]:
    return registered()
