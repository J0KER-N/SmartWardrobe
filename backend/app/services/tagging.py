from typing import Any, Dict

from . import ai_clients


async def auto_tag_image(image_bytes: bytes) -> Dict[str, Any]:
    image_b64 = ai_clients.to_base64(image_bytes)
    tags = await ai_clients.extract_garment_tags(image_b64)
    parsed = {
        "category": tags.get("category"),
        "scene": tags.get("scene"),
        "style": tags.get("style"),
        "season": tags.get("season"),
        "colorway": tags.get("colorway"),
        "extra": tags,
    }
    return parsed

