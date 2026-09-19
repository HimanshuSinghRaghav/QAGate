"""Resolve the check-library version that was live on the call date.

Not today's version. This is the difference between an audit trail and a story.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckDefinition


def checks_effective_on(db: Session, retailer_id: str, call_date: datetime
                        ) -> list[CheckDefinition]:
    stmt = select(CheckDefinition).where(
        CheckDefinition.retailer_id == retailer_id,
        CheckDefinition.effective_from <= call_date,
    )
    rows = db.execute(stmt).scalars().all()

    live = [
        row for row in rows
        if row.effective_to is None or row.effective_to > call_date
    ]
    # If several versions of one check overlap, the highest version wins.
    best: dict[str, CheckDefinition] = {}
    for row in live:
        current = best.get(row.check_id)
        if current is None or row.version > current.version:
            best[row.check_id] = row
    return sorted(best.values(), key=lambda c: (c.type, c.check_id))
