from __future__ import annotations

from typing import Iterable, List

from sqlalchemy.orm import Session

from ..models import Garment


def filter_garments_for_weather(garments: Iterable[Garment], weather: dict) -> List[Garment]:
    temperature = weather.get("temperature", 22)
    filtered = []
    for garment in garments:
        season = (garment.season or "").lower()
        if temperature < 10 and season not in {"winter", "autumn", "fall"}:
            continue
        if temperature > 25 and season in {"winter"}:
            continue
        filtered.append(garment)
    return filtered


def pick_outfit(db: Session, user_id: int, weather: dict) -> list[Garment]:
    garments = db.query(Garment).filter(Garment.owner_id == user_id, Garment.is_deleted.is_(False)).all()
    candidates = filter_garments_for_weather(garments, weather)

    outfit: list[Garment] = []
    categories = {g.category.lower(): g for g in candidates}
    for key in ["top", "bottom", "outerwear", "shoes"]:
        if key in categories:
            outfit.append(categories[key])
    if not outfit and candidates:
        outfit.append(candidates[0])
    return outfit

