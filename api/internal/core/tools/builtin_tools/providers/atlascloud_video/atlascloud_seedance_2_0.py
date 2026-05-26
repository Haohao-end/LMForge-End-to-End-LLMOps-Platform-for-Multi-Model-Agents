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
_DEFAULT_DURATION = 3
_DEFAULT_FPS = 24
_MAX_DURATION = 15
_MAX_DIMENSION = 4096


class AtlasCloudSeedance20TextToVideoArgsSchema(BaseModel):
    """Atlas Cloud Seedance 2.0 文生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=_DEFAULT_DURATION, description="视频时长，单位为秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudSeedance20ImageToVideoArgsSchema(BaseModel):
    """Atlas Cloud Seedance 2.0 图生视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    images: str = Field(description="首帧图片URL，多个URL可用逗号或换行分隔")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=_DEFAULT_DURATION, description="视频时长，单位为秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


class AtlasCloudSeedance20ReferenceToVideoArgsSchema(BaseModel):
    """Atlas Cloud Seedance 2.0 参考视频参数。"""

    prompt: str = Field(description="用于生成视频的文本提示(prompt)")
    images: str = Field(default="", description="参考图片URL，多个URL可用逗号或换行分隔")
    videos: str = Field(default="", description="参考视频URL，多个URL可用逗号或换行分隔")
    audios: str = Field(default="", description="参考音频URL，多个URL可用逗号或换行分隔")
    width: int = Field(default=_DEFAULT_WIDTH, description="输出宽度")
    height: int = Field(default=_DEFAULT_HEIGHT, description="输出高度")
    duration: int = Field(default=_DEFAULT_DURATION, description="视频时长，单位为秒")
    fps: int = Field(default=_DEFAULT_FPS, description="视频帧率")


def _normalize_dimension(value: int, default: int = _DEFAULT_WIDTH) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if 1 <= normalized <= _MAX_DIMENSION else default


def _normalize_duration(value: int, default: int = _DEFAULT_DURATION) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if 1 <= normalized <= _MAX_DURATION else default


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
    duration: int = _DEFAULT_DURATION,
    fps: int = _DEFAULT_FPS,
    images: str | None = None,
    videos: str | None = None,
    audios: str | None = None,
    require_images: bool = False,
    require_any_media: bool = False,
) -> str:
    """提交 Seedance 2.0 视频生成任务并持久化输出。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("视频生成失败：prompt 不能为空")

    normalized_width = _normalize_dimension(width, _DEFAULT_WIDTH)
    normalized_height = _normalize_dimension(height, _DEFAULT_HEIGHT)
    normalized_duration = _normalize_duration(duration)
    normalized_fps = _normalize_fps(fps)

    image_urls = parse_url_list(images)
    video_urls = parse_url_list(videos)
    audio_urls = parse_url_list(audios)

    if require_images and not image_urls:
        raise FailException("视频生成失败：至少需要一张参考图片")

    if require_any_media and not (image_urls or video_urls or audio_urls):
        raise FailException("视频生成失败：至少需要一项参考素材")

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
    if video_urls:
        payload["videos"] = video_urls
    if audio_urls:
        payload["audios"] = audio_urls

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
        f"时长: {normalized_duration} 秒",
        f"帧率: {normalized_fps}",
        "",
    ]

    if image_urls:
        result_lines.append(f"参考图片: {len(image_urls)}")
    if video_urls:
        result_lines.append(f"参考视频: {len(video_urls)}")
    if audio_urls:
        result_lines.append(f"参考音频: {len(audio_urls)}")
    if image_urls or video_urls or audio_urls:
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


@add_attribute("args_schema", AtlasCloudSeedance20TextToVideoArgsSchema)
def atlascloud_seedance_2_0_text_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_text_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 生成带原生音频的视频，适合纯文本驱动创作。",
        func=lambda prompt, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0/text-to-video",
            "source": "atlascloud-seedance-2-0-text-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
        }),
        args_schema=AtlasCloudSeedance20TextToVideoArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudSeedance20ImageToVideoArgsSchema)
def atlascloud_seedance_2_0_image_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 图生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_image_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 以前帧和可选末帧生成视频，支持原生音频。",
        func=lambda prompt, images, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0/image-to-video",
            "source": "atlascloud-seedance-2-0-image-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "require_images": True,
        }),
        args_schema=AtlasCloudSeedance20ImageToVideoArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudSeedance20ReferenceToVideoArgsSchema)
def atlascloud_seedance_2_0_reference_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 参考视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_reference_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 结合图片、视频和音频参考生成多模态视频。",
        func=lambda prompt, images="", videos="", audios="", width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0/reference-to-video",
            "source": "atlascloud-seedance-2-0-reference-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "videos": videos,
            "audios": audios,
            "require_any_media": True,
        }),
        args_schema=AtlasCloudSeedance20ReferenceToVideoArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudSeedance20TextToVideoArgsSchema)
def atlascloud_seedance_2_0_fast_text_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 Fast 文生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_fast_text_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 Fast 更快生成带原生音频的视频。",
        func=lambda prompt, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0-fast/text-to-video",
            "source": "atlascloud-seedance-2-0-fast-text-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
        }),
        args_schema=AtlasCloudSeedance20TextToVideoArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudSeedance20ImageToVideoArgsSchema)
def atlascloud_seedance_2_0_fast_image_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 Fast 图生视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_fast_image_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 Fast 以前帧和可选末帧快速生成视频。",
        func=lambda prompt, images, width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0-fast/image-to-video",
            "source": "atlascloud-seedance-2-0-fast-image-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "require_images": True,
        }),
        args_schema=AtlasCloudSeedance20ImageToVideoArgsSchema,
    )


@add_attribute("args_schema", AtlasCloudSeedance20ReferenceToVideoArgsSchema)
def atlascloud_seedance_2_0_fast_reference_to_video(**kwargs) -> StructuredTool:
    """Atlas Cloud Seedance 2.0 Fast 参考视频工具。"""
    return StructuredTool.from_function(
        name="atlascloud_seedance_2_0_fast_reference_to_video",
        description="使用 Atlas Cloud 的 Seedance 2.0 Fast 结合图片、视频和音频参考快速生成多模态视频。",
        func=lambda prompt, images="", videos="", audios="", width=_DEFAULT_WIDTH, height=_DEFAULT_HEIGHT, duration=_DEFAULT_DURATION, fps=_DEFAULT_FPS: _generate_video(**{
            **kwargs,
            "model": "bytedance/seedance-2.0-fast/reference-to-video",
            "source": "atlascloud-seedance-2-0-fast-reference-to-video",
            "prompt": prompt,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "images": images,
            "videos": videos,
            "audios": audios,
            "require_any_media": True,
        }),
        args_schema=AtlasCloudSeedance20ReferenceToVideoArgsSchema,
    )
