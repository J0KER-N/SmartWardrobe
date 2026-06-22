from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..services.engagement_metrics import build_analytics_overview

router = APIRouter(prefix="/analytics", tags=["数据看板"])


@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回用户后台可用的汇总数据。"""
    _ = current_user
    return build_analytics_overview(db)
