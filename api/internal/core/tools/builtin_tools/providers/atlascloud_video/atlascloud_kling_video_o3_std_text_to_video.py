from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from internal.exception import FailException
from internal.lib.helper import add_attribute

from ..atlascloud_shared import persist_remote_video, submit_generation_task, wait_for_prediction


class AtlasCloudKlingVideoO3StdTextToVideoArgsSchema(BaseModel):
    """Atlas Cloud Kling O3 文生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    duration: int = Field(default=5, ge=3, le=15, description="视频时长，单位为秒")
    aspect_ratio: str = Field(default="16:9", description="视频宽高比")
    sound: bool = Field(default=False, description="是否生成同步音效")


def _normalize_duration(duration: int) -> int:
    try:
        normalized = int(duration)
    except Exception:
        return 5
    return normalized if 3 <= normalized <= 15 else 5


def _normalize_aspect_ratio(aspect_ratio: str) -> str:
    allowed_ratios = {"16:9", "9:16", "1:1"}
    normalized = str(aspect_ratio or "").strip()
    return normalized if normalized in allowed_ratios else "16:9"


def _generate_video(
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    sound: bool = False,
    **kwargs,
) -> str:
    """使用 Atlas Cloud Kling O3 生成视频。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("视频生成失败：prompt 不能为空")

    model = "kwaivgi/kling-video-o3-std/text-to-video"
    normalized_duration = _normalize_duration(duration)
    normalized_aspect_ratio = _normalize_aspect_ratio(aspect_ratio)
    payload = {
        "model": model,
        "prompt": normalized_prompt,
        "duration": normalized_duration,
        "aspect_ratio": normalized_aspect_ratio,
        "sound": bool(sound),
    }

    prediction_id = submit_generation_task("generateVideo", payload)
    outputs = wait_for_prediction(
        prediction_id,
        timeout_seconds=900,
        poll_interval_seconds=3,
    )
    if not outputs:
        raise FailException("视频生成失败：未返回视频结果")

    result_lines = [
        "✓ 成功生成视频",
        f"模型: {model}",
        f"时长: {normalized_duration} 秒",
        f"比例: {normalized_aspect_ratio}",
        f"音效: {'是' if bool(sound) else '否'}",
        "",
    ]

    for idx, video_url in enumerate(outputs, 1):
        persisted_url = persist_remote_video(
            video_url,
            source="atlascloud-kling-video-o3-std",
        )
        result_lines.append(f"视频 {idx}:")
        result_lines.append(f"  URL: {persisted_url}")
        result_lines.append("")

    return "\n".join(result_lines).rstrip()


@add_attribute("args_schema", AtlasCloudKlingVideoO3StdTextToVideoArgsSchema)
def atlascloud_kling_video_o3_std_text_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Kling O3 标准文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_kling_video_o3_std_text_to_video",
        description="使用 Atlas Cloud 的 Kling O3 标准版生成视频，支持时长、比例和音效开关。",
        func=lambda prompt, duration=5, aspect_ratio="16:9", sound=False: _generate_video(**{
            **kwargs,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "sound": sound,
        }),
        args_schema=AtlasCloudKlingVideoO3StdTextToVideoArgsSchema,
    )
