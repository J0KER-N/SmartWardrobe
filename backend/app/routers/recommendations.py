from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Garment
from ..schemas import RecommendationRequest, RecommendationResponse, RecommendationItem, GarmentResponse
from ..dependencies import get_current_user
from ..services.weather import get_weather
from ..services.outfit_logic import generate_outfit_recommendations
from ..services.ai_clients import summarize_outfit

router = APIRouter(prefix="/recommendations", tags=["穿搭推荐"])

@router.post("/daily", response_model=RecommendationResponse)
def daily_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成每日穿搭推荐"""
    try:
        # 获取天气信息
        weather = get_weather(request.city)
        if not weather:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取天气信息失败"
            )
        
        # 获取用户所有衣物
        garments = db.query(Garment).filter(
            Garment.owner_id == current_user.id,
            Garment.is_deleted == False
        ).all()
        
        if not garments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="暂无衣物，请先添加衣物到衣橱"
            )
        
        # 生成穿搭推荐
        outfit_groups = generate_outfit_recommendations(garments, weather)
        recommendations = []
        
        for group in outfit_groups:
            # 获取衣物详情
            garment_responses = [
                GarmentResponse.model_validate(garment)
                for garment in group["garments"]
            ]
            # 生成穿搭描述
            description = summarize_outfit(garment_responses, weather)
            
            recommendations.append(RecommendationItem(
                garment_ids=group["garment_ids"],
                garments=garment_responses,
                description=description,
                reason=group["reason"]
            ))
        
        return RecommendationResponse(
            recommendations=recommendations,
            weather=weather
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成推荐失败: {str(e)}"
        )