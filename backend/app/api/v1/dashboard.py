from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.scoring import dashboard as svc

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def overview(retailer_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    return svc.overview(db, retailer_id)


@router.get("/dashboard/agents")
def agents(db: Session = Depends(get_db)) -> list[dict]:
    return svc.by_agent(db)


@router.get("/dashboard/repeat-offences")
def repeat_offences(db: Session = Depends(get_db)) -> list[dict]:
    return svc.repeat_offences(db)
