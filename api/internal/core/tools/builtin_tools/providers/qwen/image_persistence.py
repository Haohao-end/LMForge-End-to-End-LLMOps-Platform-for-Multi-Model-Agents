from __future__ import annotations

import os
import uuid
from urllib.parse import urlparse

import requests

from internal.service.cos_service import CosService


def _guess_image_extension(image_url: str, content_type: str = "") -> str:
    parsed = urlparse(str(image_url or ""))
    extension = os.path.splitext(parsed.path)[1].strip().lower()
    if extension in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".avif"}:
        return extension.lstrip(".")

    normalized_content_type = str(content_type or "").lower()
    if "svg" in normalized_content_type:
        return "svg"
    if "jpeg" in normalized_content_type or "jpg" in normalized_content_type:
        return "jpg"
    if "webp" in normalized_content_type:
        return "webp"
    if "gif" in normalized_content_type:
        return "gif"
    if "bmp" in normalized_content_type:
        return "bmp"
    if "avif" in normalized_content_type:
        return "avif"
    return "png"


def persist_remote_image(image_url: str, *, source: str) -> str:
    """下载第三方图片并上传到 COS，返回稳定 URL。"""
    if not image_url:
        raise ValueError("image_url is required")

    response = requests.get(image_url, timeout=60)
    response.raise_for_status()

    extension = _guess_image_extension(
        image_url=image_url,
        content_type=response.headers.get("Content-Type", ""),
    )
    filename = f"{source}_{uuid.uuid4()}.{extension}"
    return CosService.upload_bytes_without_record(
        filename=filename,
        content=response.content,
        folder="generated-images",
    )
