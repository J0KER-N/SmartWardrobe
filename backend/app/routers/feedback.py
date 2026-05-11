from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from ..database import get_db
from ..models import Feedback
from ..schemas import FeedbackCreate, FeedbackResponse, BaseResponse
from ..dependencies import get_current_user
from ..models import User
from ..services.preference_learning import update_user_pref

router = APIRouter(prefix="/feedback", tags=["用户反馈"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def post_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """接收用户对推荐的反馈并持久化，同时触发偏好更新。"""
    try:
        fb = Feedback(
            owner_id=current_user.id,
            outfit_id=feedback.outfit_id,
            action=feedback.action,
            meta=feedback.meta or {},
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)

        # 调用轻量偏好更新（非阻塞也可以，但这里同步调用便于 Demo 可见性）
        try:
            update_user_pref(current_user.id, {"action": feedback.action, **(feedback.meta or {})})
        except Exception:
            # 不阻塞主流程，记录日志即可
            pass

        return fb
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
