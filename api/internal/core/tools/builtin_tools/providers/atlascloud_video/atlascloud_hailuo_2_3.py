from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from internal.exception import FailException
from internal.lib.helper import add_attribute

from ..atlascloud_shared import (
    parse_url_list,
    persist_remote_video,
    submit_generation_task,
    wait_for_prediction,
)


_DEFAULT_WIDTH = 512
_DEFAULT_HEIGHT = 512
_DEFAULT_FPS = 24
_STANDARD_DURATIONS = (6, 10)
_FAST_DURATIONS = (6, 10)
_PRO_DURATION = 5
_MAX_DIMENSION = 4096


class AtlasCloudHailuo23T2VStandardArgsSchema(BaseModel):
    """Atlas Cloud Hailuo 2.3 标准文生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=6, description="视频时长，支持 6 或 10 秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudHailuo23T2VProArgsSchema(BaseModel):
    """Atlas Cloud Hailuo 2.3 Pro 文生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudHailuo23I2VStandardArgsSchema(BaseModel):
    """Atlas Cloud Hailuo 2.3 标准图生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    images: str = Field(description="参考图片URL，多个URL可用逗号或换行分隔")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=6, description="视频时长，支持 6 或 10 秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudHailuo23I2VProArgsSchema(BaseModel):
    """Atlas Cloud Hailuo 2.3 Pro 图生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    images: str = Field(description="参考图片URL，多个URL可用逗号或换行分隔")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudHailuo23FastArgsSchema(BaseModel):
    """Atlas Cloud Hailuo 2.3 Fast 参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    images: str = Field(default="", description="参考图片URL，多个URL可用逗号或换行分隔")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=6, description="视频时长，支持 6 或 10 秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


def _normalize_dimension(value: int, default: int = _DEFAULT_WIDTH) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if 1 <= normalized <= _MAX_DIMENSION else default


def _normalize_duration(value: int, allowed_durations: tuple[int, ...], default: int) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if normalized in allowed_durations else default


def _normalize_fps(value: int, default: int = _DEFAULT_FPS) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if 1 <= normalized <= 60 else default


def _generate_video(
    *,
    model: str,
    source: str,
    prompt: str,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    duration: int = _PRO_DURATION,
    fps: int = _DEFAULT_FPS,
    images: str | None = None,
    allowed_durations: tuple[int, ...] = _STANDARD_DURATIONS,
    duration_default: int = 6,
    duration_suffix: str = "",
    require_images: bool = False,
) -> str:
    """提交 Hailuo 2.3 视频生成任务并持久化输出。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("视频生成失败：prompt 不能为空")

    normalized_width = _normalize_dimension(width, _DEFAULT_WIDTH)
    normalized_height = _normalize_dimension(height, _DEFAULT_HEIGHT)
    normalized_duration = _normalize_duration(duration, allowed_durations, duration_default)
    normalized_fps = _normalize_fps(fps)
    image_urls = parse_url_list(images)

    if require_images and not image_urls:
        raise FailException("视频生成失败：至少需要一张参考图片")

    payload = {
        "model": model,
        "prompt": normalized_prompt,
        "width": normalized_width,
        "height": normalized_height,
        "duration": normalized_duration,
        "fps": normalized_fps,
    }
    if image_urls:
        payload["images"] = image_urls

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
        f"宽度: {normalized_width}",
        f"高度: {normalized_height}",
        f"时长: {normalized_duration} 秒{duration_suffix}",
        f"帧率: {normalized_fps}",
        "",
    ]

    if image_urls:
        result_lines.append(f"参考图片: {len(image_urls)}")
        result_lines.append("")

    for idx, video_url in enumerate(outputs, 1):
        persisted_url = persist_remote_video(
            video_url,
            source=source,
        )
        result_lines.append(f"视频 {idx}:")
        result_lines.append(f"  URL: {persisted_url}")
        result_lines.append("")

    return "\n".join(result_lines).rstrip()


@add_attribute("args_schema", AtlasCloudHailuo23T2VStandardArgsSchema)
def atlascloud_hailuo_2_3_t2v_standard(**kwargs) -> StructuredTool:
    """Atlas Cloud Hailuo 2.3 标准文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_hailuo_2_3_t2v_standard",
        description="使用 Atlas Cloud 的 Hailuo 2.3 Standard 生成 1080p 电影级视频，支持 6 秒或 10 秒时长。",
        func=lambda prompt, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=6, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "minimax/hailuo-2.3/t2v-standard",
            "source": "atlascloud-hailuo-2-3-t2v-standard",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "allowed_durations": _STANDARD_DURATIONS,
            "duration_default": 6,
        }),
        args_schema=AtlasCloudHailuo23T2VStandardArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudHailuo23T2VProArgsSchema)
def atlascloud_hailuo_2_3_t2v_pro(**kwargs) -> StructuredTool:
    """Atlas Cloud Hailuo 2.3 Pro 文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_hailuo_2_3_t2v_pro",
        description="使用 Atlas Cloud 的 Hailuo 2.3 Pro 生成高保真 1080p 视频，时长固定为 5 秒。",
        func=lambda prompt, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "minimax/hailuo-2.3/t2v-pro",
            "source": "atlascloud-hailuo-2-3-t2v-pro",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": _PRO_DURATION,
            "fps": fps,
            "allowed_durations": (_PRO_DURATION,),
            "duration_default": _PRO_DURATION,
            "duration_suffix": "（固定）",
        }),
        args_schema=AtlasCloudHailuo23T2VProArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudHailuo23I2VStandardArgsSchema)
def atlascloud_hailuo_2_3_i2v_standard(**kwargs) -> StructuredTool:
    """Atlas Cloud Hailuo 2.3 标准图生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_hailuo_2_3_i2v_standard",
        description="使用 Atlas Cloud 的 Hailuo 2.3 Standard 以单张参考图生成 1080p 视频，支持 6 秒或 10 秒时长。",
        func=lambda prompt, images, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=6, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "minimax/hailuo-2.3/i2v-standard",
            "source": "atlascloud-hailuo-2-3-i2v-standard",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "allowed_durations": _STANDARD_DURATIONS,
            "duration_default": 6,
            "require_images": True,
        }),
        args_schema=AtlasCloudHailuo23I2VStandardArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudHailuo23I2VProArgsSchema)
def atlascloud_hailuo_2_3_i2v_pro(**kwargs) -> StructuredTool:
    """Atlas Cloud Hailuo 2.3 Pro 图生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_hailuo_2_3_i2v_pro",
        description="使用 Atlas Cloud 的 Hailuo 2.3 Pro 以单张参考图生成高保真 1080p 视频，时长固定为 5 秒。",
        func=lambda prompt, images, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "minimax/hailuo-2.3/i2v-pro",
            "source": "atlascloud-hailuo-2-3-i2v-pro",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": _PRO_DURATION,
            "fps": fps,
            "images": images,
            "allowed_durations": (_PRO_DURATION,),
            "duration_default": _PRO_DURATION,
            "duration_suffix": "（固定）",
            "require_images": True,
        }),
        args_schema=AtlasCloudHailuo23I2VProArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudHailuo23FastArgsSchema)
def atlascloud_hailuo_2_3_fast(**kwargs) -> StructuredTool:
    """Atlas Cloud Hailuo 2.3 Fast 工具。"""
    return StructuredTool.from_function(
        name="atlascloud_hailuo_2_3_fast",
        description="使用 Atlas Cloud 的 Hailuo 2.3 Fast 快速生成 1080p 视频，可选参考图。",
        func=lambda prompt, images="", width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=6, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "minimax/hailuo-2.3/fast",
            "source": "atlascloud-hailuo-2-3-fast",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "allowed_durations": _FAST_DURATIONS,
            "duration_default": 6,
        }),
        args_schema=AtlasCloudHailuo23FastArgsSchema,
    )
