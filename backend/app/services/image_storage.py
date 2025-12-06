import io
import uuid
from pathlib import Path
from typing import BinaryIO

from PIL import Image
from fastapi import HTTPException, status

from ..config import get_settings

settings = get_settings()
MEDIA_ROOT = Path(settings.media_root)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


class ImageStorageError(Exception):
    """Base exception for image storage operations."""


def validate_image_format(filename: str) -> None:
    """Validate image file format."""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in settings.allowed_image_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format. Allowed: {', '.join(settings.allowed_image_formats)}",
        )


def validate_image_size(binary: bytes) -> None:
    """Validate image file size."""
    max_size = settings.max_image_size_mb * 1024 * 1024
    if len(binary) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size: {settings.max_image_size_mb}MB",
        )


def compress_image(binary: bytes, quality: int | None = None) -> bytes:
    """Compress image while maintaining quality."""
    try:
        img = Image.open(io.BytesIO(binary))
        # Convert RGBA to RGB if necessary (for JPEG)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if too large
        max_dim = settings.image_max_dimension
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality or settings.image_quality, optimize=True)
        return output.getvalue()
    except Exception as e:
        raise ImageStorageError(f"Failed to process image: {str(e)}") from e


def save_temp_image(binary: bytes, suffix: str = ".png", compress: bool = True) -> str:
    """Save image to local storage or object storage."""
    # Validate format
    if suffix.startswith("."):
        ext = suffix[1:].lower()
    else:
        ext = suffix.lower()
    if ext not in settings.allowed_image_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {ext}",
        )

    # Validate size
    validate_image_size(binary)

    # Compress if needed
    if compress and ext in ("jpg", "jpeg", "png"):
        try:
            binary = compress_image(binary)
            suffix = ".jpg"  # Compressed images are saved as JPEG
        except ImageStorageError:
            pass  # If compression fails, use original

    # Save to storage
    if settings.object_storage_type == "local":
        return _save_local(binary, suffix)
    else:
        return _save_to_object_storage(binary, suffix)


def _save_local(binary: bytes, suffix: str) -> str:
    """Save image to local filesystem."""
    file_id = f"{uuid.uuid4().hex}{suffix}"
    file_path = MEDIA_ROOT / file_id
    file_path.write_bytes(binary)
    return str(file_path)


def _save_to_object_storage(binary: bytes, suffix: str) -> str:
    """Save image to object storage (S3/OSS/Qiniu)."""
    # TODO: Implement actual object storage integration
    # For now, fallback to local storage
    return _save_local(binary, suffix)


def build_public_url(file_path: str) -> str:
    """Build public URL for image."""
    if settings.object_storage_type == "local":
        # For local storage, return relative path or construct full URL
        # In production, you might want to serve via nginx/CDN
        if settings.is_production and settings.frontend_origin:
            base_url = str(settings.frontend_origin).rstrip("/")
            # Extract relative path
            rel_path = str(file_path).replace(str(MEDIA_ROOT), "").lstrip("/")
            return f"{base_url}/media/{rel_path}"
        return file_path
    else:
        # TODO: Generate signed URL for object storage
        # For S3: return presigned URL
        # For OSS: return public URL with signature
        return file_path


def delete_image(file_path: str) -> None:
    """Delete image from storage."""
    if settings.object_storage_type == "local":
        path = Path(file_path)
        if path.exists():
            path.unlink()
    else:
        # TODO: Delete from object storage
        pass

