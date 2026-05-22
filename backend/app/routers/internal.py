from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..services.rules_engine import get_default_engine
from ..models import Garment, User

router = APIRouter(prefix="/internal", tags=["内部（Mock）"])


class MockRecommendRequest(BaseModel):
    n: Optional[int] = 3
    garments: Optional[List[dict]] = None


@router.post("/mock_recommend")
def mock_recommend(
    body: MockRecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回基于规则引擎的 N 个候选（用于本地验证）。

    如果请求中提供 `garments` 列表，则直接使用；否则从当前用户衣橱读取并转换为引擎可用的字典格式。
    """
    engine = get_default_engine()

    garments_input = body.garments
    if not garments_input:
        # 从 DB 中读取用户的衣物
        db_garments = db.query(Garment).filter(Garment.owner_id == current_user.id, Garment.is_deleted == False).all()
        if not db_garments:
            raise HTTPException(status_code=400, detail="用户衣橱为空，无法生成推荐")

        garments_input = []
        for g in db_garments:
            garments_input.append({
                "id": g.id,
                "color": g.color or "",
                # 兼容旧 schema：将 tags 中可能的风格取第一个作为 style
                "style": (g.tags[0] if g.tags and len(g.tags) > 0 else None),
                "tags": g.tags or [],
            })

    candidates = engine.recommend(garments_input, n=body.n or 3, context={})

    return {"candidates": candidates, "count": len(candidates)}
