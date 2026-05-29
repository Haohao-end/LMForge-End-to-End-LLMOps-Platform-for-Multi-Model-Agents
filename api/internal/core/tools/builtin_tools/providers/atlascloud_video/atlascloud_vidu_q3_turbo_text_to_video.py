from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from internal.exception import FailException
from internal.lib.helper import add_attribute

from ..atlascloud_shared import persist_remote_video, submit_generation_task, wait_for_prediction


class AtlasCloudViduQ3TurboTextToVideoArgsSchema(BaseModel):
    """Atlas Cloud Vidu Q3 Turbo 文生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    resolution: str = Field(default="720p", description="输出分辨率")
    duration: int = Field(default=5, ge=1, le=16, description="视频时长，单位为秒")
    aspect_ratio: str = Field(default="16:9", description="视频宽高比")
    movement_amplitude: str = Field(default="auto", description="运动幅度")
    generate_audio: bool = Field(default=True, description="是否生成音频")
    bgm: bool = Field(default=True, description="是否生成背景音乐")
    seed: int = Field(default=-1, description="随机种子，-1 表示随机")


def _normalize_resolution(resolution: str) -> str:
    allowed_resolutions = {"540p", "720p", "1080p"}
    normalized = str(resolution or "").strip().lower()
    return normalized if normalized in allowed_resolutions else "720p"


def _normalize_duration(duration: int) -> int:
    try:
        normalized = int(duration)
    except Exception:
        return 5
    return normalized if 1 <= normalized <= 16 else 5


def _normalize_aspect_ratio(aspect_ratio: str) -> str:
    allowed_ratios = {"16:9", "4:3", "9:16"}
    normalized = str(aspect_ratio or "").strip()
    return normalized if normalized in allowed_ratios else "16:9"


def _normalize_movement_amplitude(movement_amplitude: str) -> str:
    allowed_levels = {"auto", "small", "medium", "large"}
    normalized = str(movement_amplitude or "").strip().lower()
    return normalized if normalized in allowed_levels else "auto"


def _normalize_seed(seed: int) -> int:
    try:
        return int(seed)
    except Exception:
        return -1


def _generate_video(
    prompt: str,
    resolution: str = "720p",
    duration: int = 5,
    aspect_ratio: str = "16:9",
    movement_amplitude: str = "auto",
    generate_audio: bool = True,
    bgm: bool = True,
    seed: int = -1,
    **kwargs,
) -> str:
    """使用 Atlas Cloud Vidu Q3 Turbo 生成视频。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("视频生成失败：prompt 不能为空")

    model = "vidu/q3-turbo/text-to-video"
    normalized_resolution = _normalize_resolution(resolution)
    normalized_duration = _normalize_duration(duration)
    normalized_aspect_ratio = _normalize_aspect_ratio(aspect_ratio)
    normalized_movement_amplitude = _normalize_movement_amplitude(movement_amplitude)
    normalized_seed = _normalize_seed(seed)
    payload = {
        "model": model,
        "prompt": normalized_prompt,
        "resolution": normalized_resolution,
        "duration": normalized_duration,
        "aspect_ratio": normalized_aspect_ratio,
        "movement_amplitude": normalized_movement_amplitude,
        "generate_audio": bool(generate_audio),
        "bgm": bool(bgm),
        "seed": normalized_seed,
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
        f"分辨率: {normalized_resolution}",
        f"时长: {normalized_duration} 秒",
        f"比例: {normalized_aspect_ratio}",
        f"运动幅度: {normalized_movement_amplitude}",
        f"音频: {'是' if bool(generate_audio) else '否'}",
        f"BGM: {'是' if bool(bgm) else '否'}",
        f"种子: {normalized_seed}",
        "",
    ]

    for idx, video_url in enumerate(outputs, 1):
        persisted_url = persist_remote_video(
            video_url,
            source="atlascloud-vidu-q3-turbo",
        )
        result_lines.append(f"视频 {idx}:")
        result_lines.append(f"  URL: {persisted_url}")
        result_lines.append("")

    return "\n".join(result_lines).rstrip()


@add_attribute("args_schema", AtlasCloudViduQ3TurboTextToVideoArgsSchema)
def atlascloud_vidu_q3_turbo_text_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Vidu Q3 Turbo 文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_vidu_q3_turbo_text_to_video",
        description="使用 Atlas Cloud 的 Vidu Q3 Turbo 生成视频，支持分辨率、比例、运动幅度和音频控制。",
        func=lambda prompt, resolution="720p", duration=5, aspect_ratio="16:9", movement_amplitude="auto", generate_audio=True, bgm=True, seed=-1: _generate_video(**{
            **kwargs,
            "prompt": prompt,
            "resolution": resolution,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "movement_amplitude": movement_amplitude,
            "generate_audio": generate_audio,
            "bgm": bgm,
            "seed": seed,
        }),
        args_schema=AtlasCloudViduQ3TurboTextToVideoArgsSchema,
    )
