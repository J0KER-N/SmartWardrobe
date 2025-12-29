import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def generate_outfit_recommendations(garments: List, weather: Dict) -> List[Dict]:
    """生成穿搭推荐"""
    temp = weather.get("temp_c", 20)
    condition = weather.get("condition", "晴")
    
    # 按温度分类衣物
    warm_garments = []  # 保暖衣物（外套、毛衣、长裤）
    cool_garments = []  # 清凉衣物（短袖、短裤、裙子）
    all_garments = []   # 所有衣物
    
    for g in garments:
        tags = g.tags or []
        all_garments.append({
            "id": g.id,
            "category": g.category,
            "tags": tags,
            "garment": g
        })
        
        # 按标签分类
        if any(tag in tags for tag in ["外套", "毛衣", "长裤", "冬季", "秋季"]):
            warm_garments.append(g.id)
        if any(tag in tags for tag in ["短袖", "短裤", "裙子", "夏季", "春季"]):
            cool_garments.append(g.id)
    
    # 生成推荐组合
    recommendations = []
    
    # 高温（>25℃）
    if temp > 25:
        # 筛选清凉上衣+下装
        tops = [g for g in all_garments if g["category"] in ["上衣", "短袖"] and "清凉" in g["tags"]]
        bottoms = [g for g in all_garments if g["category"] in ["裤子", "短裤", "裙子"] and "清凉" in g["tags"]]
        
        if tops and bottoms:
            recommendations.append({
                "garment_ids": [tops[0]["id"], bottoms[0]["id"]],
                "garments": [tops[0]["garment"], bottoms[0]["garment"]],
                "reason": "高温天气，推荐清凉透气的搭配"
            })
    
    # 中温（15-25℃）
    elif 15 <= temp <= 25:
        # 常规搭配
        tops = [g for g in all_garments if g["category"] in ["上衣", "长袖"]]
        bottoms = [g for g in all_garments if g["category"] in ["裤子", "长裙"]]
        
        if tops and bottoms:
            recommendations.append({
                "garment_ids": [tops[0]["id"], bottoms[0]["id"]],
                "garments": [tops[0]["garment"], bottoms[0]["garment"]],
                "reason": "温度适宜，推荐舒适日常搭配"
            })
    
    # 低温（<15℃）
    else:
        # 保暖搭配
        outerwear = [g for g in all_garments if g["category"] == "外套"]
        tops = [g for g in all_garments if g["category"] == "毛衣"]
        bottoms = [g for g in all_garments if g["category"] == "长裤"]
        
        if outerwear and tops and bottoms:
            recommendations.append({
                "garment_ids": [outerwear[0]["id"], tops[0]["id"], bottoms[0]["id"]],
                "garments": [outerwear[0]["garment"], tops[0]["garment"], bottoms[0]["garment"]],
                "reason": "低温天气，推荐保暖多层搭配"
            })
    
    # 雨天特殊推荐
    if "雨" in condition or "雪" in condition:
        rain_garments = [g for g in all_garments if "防水" in g["tags"] or "雨衣" in g["tags"]]
        if rain_garments:
            recommendations.append({
                "garment_ids": [rain_garments[0]["id"]],
                "garments": [rain_garments[0]["garment"]],
                "reason": "雨天推荐防水衣物"
            })
    
    # 兜底推荐（如果没有匹配的）
    if not recommendations and all_garments:
        recommendations.append({
            "garment_ids": [all_garments[0]["id"]],
            "garments": [all_garments[0]["garment"]],
            "reason": "基于你的衣橱推荐的搭配"
        })
    
    return recommendations