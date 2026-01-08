from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from ..database import get_db
from ..models import User, Garment, RecommendationRecord
from ..schemas import RecommendationRequest, RecommendationResponse, RecommendationItem, GarmentResponse
from ..dependencies import get_current_user
from ..services.weather import get_weather
from ..services.outfit_logic import generate_outfit_recommendations
from ..services.ai_clients import summarize_outfit, generate_recommendation_reason

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
            # 生成推荐理由（使用百川大模型，包含天气信息）
            # 从 group 中获取 style 和 color（如果存在）
            style = group.get("style")
            color = group.get("color")
            # 如果没有直接提供，尝试从 reason 文本中提取
            if not style or not color:
                reason_text = group.get("reason", "")
                if not style and "风格" in reason_text:
                    for s in ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古"]:
                        if s in reason_text:
                            style = s
                            break
                if not color and "系" in reason_text:
                    for c in ["深色", "浅色", "亮色", "暖色", "冷色"]:
                        if c in reason_text:
                            color = c
                            break
            
            reason = generate_recommendation_reason(garment_responses, weather, style, color)

            item = RecommendationItem(
                garment_ids=group["garment_ids"],
                garments=garment_responses,
                description=description,
                reason=reason
            )
            recommendations.append(item)

            # 将推荐写入历史记录
            # 使用 model_dump(mode='json') 确保 datetime 对象被转换为字符串
            record = RecommendationRecord(
                owner_id=current_user.id,
                garment_ids=item.garment_ids,
                garments=[g.model_dump(mode='json') for g in garment_responses],
                description=item.description,
                reason=item.reason
            )
            db.add(record)

        db.commit()

        return RecommendationResponse(
            recommendations=recommendations,
            weather=weather
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
        # 获取天气信息
        weather = get_weather(city)
        if not weather:
            # 如果获取天气失败，使用默认天气数据
            weather = {
                "temp_c": 20,
                "condition": "晴",
                "city": city
            }
        
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
        
        # 生成多组推荐（3-5组）
        outfit_groups = generate_outfit_recommendations(garments, weather)
        
        # 如果推荐数量不足，随机组合生成更多推荐
        while len(outfit_groups) < 3 and len(garments) >= 2:
            # 随机选择2-3件衣物组合
            selected = random.sample(garments, min(3, len(garments)))
            styles = ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古"]
            colors = ["深色", "浅色", "亮色", "暖色", "冷色"]
            style = random.choice(styles)
            color = random.choice(colors)
            
            outfit_groups.append({
                "garment_ids": [g.id for g in selected],
                "garments": selected,
                "style": style,  # 保存 style 信息
                "color": color,   # 保存 color 信息
                "reason": f"{style}风格，{color}系搭配，适合当前天气"  # 保留作为备用
            })
        
        # 限制最多5组推荐
        outfit_groups = outfit_groups[:5]
        
        recommendations = []
        
        for group in outfit_groups:
            # 获取衣物详情
            garment_responses = [
                GarmentResponse.model_validate(garment)
                for garment in group["garments"]
            ]
            # 生成穿搭描述
            description = summarize_outfit(garment_responses, weather)
            # 生成推荐理由（使用百川大模型，包含天气信息）
            # 从 group 中获取 style 和 color（如果存在）
            style = group.get("style")
            color = group.get("color")
            # 如果没有直接提供，尝试从 reason 文本中提取
            if not style or not color:
                reason_text = group.get("reason", "")
                if not style and "风格" in reason_text:
                    for s in ["简约", "时尚", "休闲", "正式", "运动", "甜美", "复古"]:
                        if s in reason_text:
                            style = s
                            break
                if not color and "系" in reason_text:
                    for c in ["深色", "浅色", "亮色", "暖色", "冷色"]:
                        if c in reason_text:
                            color = c
                            break
            
            reason = generate_recommendation_reason(garment_responses, weather, style, color)

            item = RecommendationItem(
                garment_ids=group["garment_ids"],
                garments=garment_responses,
                description=description,
                reason=reason
            )
            recommendations.append(item)

            # 将推荐写入历史记录
            # 使用 model_dump(mode='json') 确保 datetime 对象被转换为字符串
            record = RecommendationRecord(
                owner_id=current_user.id,
                garment_ids=item.garment_ids,
                garments=[g.model_dump(mode='json') for g in garment_responses],
                description=item.description,
                reason=item.reason
            )
            db.add(record)

        db.commit()

        return RecommendationResponse(
            recommendations=recommendations,
            weather=weather
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"自动生成推荐失败: {str(e)}"
        )