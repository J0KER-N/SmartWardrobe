from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import UserFeedback
from ..schemas import UserFeedbackCreate, UserFeedbackResponse

router = APIRouter(prefix="/internal", tags=["内部接口"])

@router.post("/feedback", response_model=UserFeedbackResponse, status_code=status.HTTP_201_CREATED)
def collect_feedback(
    feedback: UserFeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    接收用户对推荐或物品的反馈并持久化（供离线重排使用）。
    内部接口，直接接收 user_id。
    """
    if feedback.event_type not in ["like", "save", "click", "view"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="event_type must be one of: like, save, click, view"
        )
    
    try:
        new_feedback = UserFeedback(
            user_id=feedback.user_id,
            item_id=feedback.item_id,
            event_type=feedback.event_type,
            context=feedback.context or {},
            timestamp=datetime.utcnow()
        )
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)

        return new_feedback
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
