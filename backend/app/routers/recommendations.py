from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from ..database import get_db
from ..models import User, Garment, RecommendationRecord
from ..schemas import RecommendationRequest, RecommendationResponse, RecommendationItem, GarmentResponse
from ..dependencies import get_current_user
from ..services.agent_orchestrator import run_recommendation_pipeline

router = APIRouter(prefix="/recommendations", tags=["穿搭推荐"])

@router.post("/daily", response_model=RecommendationResponse)
def daily_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成每日穿搭推荐"""
    try:
        pipeline = run_recommendation_pipeline(
            db=db,
            current_user=current_user,
            city=request.city,
            allow_weather_fallback=False,
            allow_random_fallback=True,
        )

        return RecommendationResponse(
            recommendations=pipeline.recommendations,
            weather=pipeline.weather,
        )
    
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成推荐失败: {str(e)}"
        )

@router.get("/auto", response_model=RecommendationResponse)
def auto_recommendations(
    city: Optional[str] = "北京",  # 默认城市，前端可以传递用户位置
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """自动生成推荐（根据用户衣橱、天气、随机风格）"""
    try:
        pipeline = run_recommendation_pipeline(
            db=db,
            current_user=current_user,
            city=city or "北京",
            allow_weather_fallback=True,
            allow_random_fallback=True,
        )

        return RecommendationResponse(
            recommendations=pipeline.recommendations,
            weather=pipeline.weather,
        )
    
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"自动生成推荐失败: {str(e)}"
        )