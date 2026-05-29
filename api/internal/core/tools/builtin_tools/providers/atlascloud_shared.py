from __future__ import annotations

import json
import os
import time
import uuid
from urllib.parse import urlparse

import requests

from internal.exception import FailException
from internal.service.cos_service import CosService


_DEFAULT_MODEL_API_BASE = "https://api.atlascloud.ai/api/v1/model"
_SUCCESS_STATUSES = {"completed", "succeeded", "success", "done"}
_FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}


def resolve_atlascloud_api_key() -> str:
    """解析 Atlas Cloud 的 API Key。"""
    return os.getenv("ATLASCLOUD_API_KEY", "") or os.getenv("ATLAS_CLOUD_API_KEY", "")


def resolve_atlascloud_model_api_base() -> str:
    """解析 Atlas Cloud 图像/视频模型 API base。"""
    base = (
        os.getenv("ATLASCLOUD_MODEL_API_BASE", "")
        or os.getenv("ATLAS_CLOUD_MODEL_API_BASE", "")
        or _DEFAULT_MODEL_API_BASE
    )
    return base.rstrip("/")


def _build_headers() -> dict[str, str]:
    api_key = resolve_atlascloud_api_key()
    if not api_key:
        raise FailException("未配置ATLASCLOUD_API_KEY环境变量")

    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text.strip()

    if not isinstance(payload, dict):
        return str(payload).strip()

    error = payload.get("error")
    if isinstance(error, dict):
        detail = error.get("message") or error.get("detail") or error.get("error")
        if detail:
            return str(detail).strip()

    for key in ("message", "msg", "error", "detail"):
        detail = payload.get(key)
        if detail:
            return str(detail).strip()

    return ""


def _request_json(
    method: str,
    url: str,
    *,
    json_body: dict | None = None,
    timeout_seconds: int = 60,
) -> dict:
    response = requests.request(
        method,
        url,
        headers=_build_headers(),
        json=json_body,
        timeout=timeout_seconds,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = _extract_error_message(response)
        message = f"Atlas Cloud 请求失败：HTTP {response.status_code}"
        if detail:
            message = f"{message} - {detail}"
        raise FailException(message) from exc

    try:
        payload = response.json()
    except Exception as exc:
        raise FailException("Atlas Cloud 响应不是有效 JSON") from exc

    if isinstance(payload, dict):
        code = payload.get("code")
        if code not in (None, 0, "0", 200, "200"):
            message = payload.get("message") or payload.get("msg") or payload.get("error")
            raise FailException(f"Atlas Cloud 请求失败：{message or '未知错误'}")
        return payload

    return {"data": payload}


def submit_generation_task(
    endpoint: str,
    payload: dict,
    *,
    timeout_seconds: int = 60,
) -> str:
    """提交 Atlas Cloud 图像/视频任务并返回 prediction id。"""
    url = f"{resolve_atlascloud_model_api_base()}/{endpoint.lstrip('/')}"
    response = _request_json("POST", url, json_body=payload, timeout_seconds=timeout_seconds)

    prediction_id = ""
    if isinstance(response, dict):
        for key in ("id", "prediction_id", "predictionId"):
            value = response.get(key)
            if value:
                prediction_id = str(value)
                break

        if not prediction_id and isinstance(response.get("data"), dict):
            data = response["data"]
            for key in ("id", "prediction_id", "predictionId"):
                value = data.get(key)
                if value:
                    prediction_id = str(value)
                    break

    if not prediction_id:
        raise FailException("Atlas Cloud 生成任务提交失败：未返回 prediction ID")

    return prediction_id


def wait_for_prediction(
    prediction_id: str,
    *,
    timeout_seconds: int = 600,
    poll_interval_seconds: int = 3,
) -> list[str]:
    """轮询 Atlas Cloud 任务直至完成并返回输出 URL 列表。"""
    deadline = time.monotonic() + timeout_seconds
    poll_url = f"{resolve_atlascloud_model_api_base()}/prediction/{prediction_id}"
    last_status = ""

    while True:
        response = _request_json("GET", poll_url, timeout_seconds=60)
        payload: dict[str, object]
        if isinstance(response.get("data"), dict):
            payload = response["data"]
        else:
            payload = response

        status = str(payload.get("status") or response.get("status") or "").lower().strip()
        last_status = status

        if status in _SUCCESS_STATUSES:
            outputs = _extract_output_urls(payload)
            if not outputs:
                outputs = _extract_output_urls(response)
            return outputs

        if status in _FAILED_STATUSES:
            error = payload.get("error") or payload.get("message") or response.get("error") or response.get("message")
            raise FailException(f"Atlas Cloud 生成失败：{error or '未知错误'}")

        if time.monotonic() >= deadline:
            raise FailException(f"Atlas Cloud 生成超时：{prediction_id} ({last_status or 'unknown'})")

        time.sleep(poll_interval_seconds)


def parse_url_list(raw_urls: str | None) -> list[str]:
    """解析逗号/换行分隔的 URL 字符串。"""
    normalized = str(raw_urls or "").strip()
    if not normalized:
        return []

    if normalized.startswith("[") and normalized.endswith("]"):
        try:
            parsed = json.loads(normalized)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

    for separator in ("\r\n", "\n", ";", ","):
        normalized = normalized.replace(separator, "\n")

    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _extract_output_urls(node: object) -> list[str]:
    """从 Atlas Cloud 任务结果里提取输出 URL。"""
    collected: list[str] = []

    if isinstance(node, str):
        value = node.strip()
        if value:
            collected.append(value)
    elif isinstance(node, list):
        for item in node:
            collected.extend(_extract_output_urls(item))
    elif isinstance(node, dict):
        for key in ("url", "download_url", "file_url", "output_url", "video_url", "image_url"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                collected.append(value.strip())

        for key in ("outputs", "output", "result", "data"):
            nested = node.get(key)
            if nested is not None:
                collected.extend(_extract_output_urls(nested))

    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in collected:
        if value not in seen:
            seen.add(value)
            deduplicated.append(value)
    return deduplicated


def _guess_extension(asset_url: str, content_type: str, *, kind: str) -> str:
    """根据 URL 或内容类型猜测文件扩展名。"""
    parsed = urlparse(str(asset_url or ""))
    extension = os.path.splitext(parsed.path)[1].strip().lower().lstrip(".")

    if kind == "video":
        allowed_extensions = {"mp4", "webm", "mov", "mkv", "avi", "gif"}
        default_extension = "mp4"
    else:
        allowed_extensions = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "svg", "avif"}
        default_extension = "png"

    if extension in allowed_extensions:
        return extension

    normalized_content_type = str(content_type or "").lower()
    if "svg" in normalized_content_type and "svg" in allowed_extensions:
        return "svg"
    if "jpeg" in normalized_content_type or "jpg" in normalized_content_type:
        return "jpg"
    if "png" in normalized_content_type:
        return "png"
    if "webp" in normalized_content_type and "webp" in allowed_extensions:
        return "webp"
    if "gif" in normalized_content_type and "gif" in allowed_extensions:
        return "gif"
    if "bmp" in normalized_content_type and "bmp" in allowed_extensions:
        return "bmp"
    if "avif" in normalized_content_type and "avif" in allowed_extensions:
        return "avif"
    if "mp4" in normalized_content_type:
        return "mp4"
    if "webm" in normalized_content_type:
        return "webm"
    if "quicktime" in normalized_content_type or "mov" in normalized_content_type:
        return "mov"
    if "x-msvideo" in normalized_content_type or "avi" in normalized_content_type:
        return "avi"
    if "matroska" in normalized_content_type or "mkv" in normalized_content_type:
        return "mkv"

    return default_extension


def _persist_remote_asset(asset_url: str, *, source: str, folder: str, kind: str) -> str:
    """下载 Atlas Cloud 生成的远程资源并保存到 COS。"""
    if not asset_url:
        raise FailException("Atlas Cloud 生成失败：未返回资源 URL")

    response = requests.get(asset_url, timeout=120)
    response.raise_for_status()

    extension = _guess_extension(
        asset_url,
        response.headers.get("Content-Type", ""),
        kind=kind,
    )
    filename = f"{source}_{uuid.uuid4().hex}.{extension}"
    return CosService.upload_bytes_without_record(
        filename=filename,
        content=response.content,
        folder=folder,
    )


def persist_remote_image(image_url: str, *, source: str) -> str:
    """下载图像并保存到 COS。"""
    return _persist_remote_asset(
        image_url,
        source=source,
        folder="generated-images",
        kind="image",
    )


def persist_remote_video(video_url: str, *, source: str) -> str:
    """下载视频并保存到 COS。"""
    return _persist_remote_asset(
        video_url,
        source=source,
        folder="generated-videos",
        kind="video",
    )
