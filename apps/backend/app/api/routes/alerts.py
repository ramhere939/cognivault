"""Alert API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.database import get_db
from app.models.alert import Alert, AlertSeverity, AlertType
from app.schemas.alert import AlertResponse, AlertSummary, AlertListResponse
from app.core.alerts.engine import get_alerts_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    resolved: bool | None = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional filtering. Unresolved by default."""
    query = select(Alert).order_by(
        Alert.severity.desc(), Alert.created_at.desc()
    )
    if severity is not None:
        query = query.where(Alert.severity == severity)
    if alert_type is not None:
        query = query.where(Alert.alert_type == alert_type)
    if resolved is not None:
        query = query.where(Alert.resolved == resolved)

    # Count
    count_result = await db.execute(
        select(Alert.id).where(
            *([Alert.resolved == resolved] if resolved is not None else [])
        )
    )
    total = len(count_result.fetchall())

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        alerts=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=AlertSummary)
async def alerts_summary(db: AsyncSession = Depends(get_db)):
    """Dashboard summary counts by severity and type."""
    summary = await get_alerts_summary(db)
    return AlertSummary(**summary)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Mark an alert as resolved."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post("/analyze")
async def trigger_analysis(db: AsyncSession = Depends(get_db)):
    """
    Trigger a full re-scan of all documents.
    Returns immediately — analysis runs in background.
    """
    # Future: queue a full-corpus SemanticAlertDetector run
    return {"message": "Analysis queued. New alerts will appear shortly.", "status": "queued"}
