from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from internal.exception import FailException
from internal.lib.helper import add_attribute

from ..atlascloud_shared import persist_remote_image, submit_generation_task, wait_for_prediction


class AtlasCloudGPTImage2TextToImageArgsSchema(BaseModel):
    """Atlas Cloud GPT Image 2 文生图参数。"""

    prompt: str = Field(description="用于生成图片的文本提示(prompt)")
    size: str = Field(default="1024x1024", description="输出图片尺寸")
    quality: str = Field(default="medium", description="输出图片质量")


def _normalize_size(size: str) -> str:
    allowed_sizes = {"1024x1024", "1024x1536", "1536x1024"}
    normalized = str(size or "").strip()
    return normalized if normalized in allowed_sizes else "1024x1024"


def _normalize_quality(quality: str) -> str:
    allowed_qualities = {"low", "medium", "high"}
    normalized = str(quality or "").strip().lower()
    return normalized if normalized in allowed_qualities else "medium"


def _generate_image(prompt: str, size: str = "1024x1024", quality: str = "medium", **kwargs) -> str:
    """使用 Atlas Cloud GPT Image 2 生成图像。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("图像生成失败：prompt 不能为空")

    model = "openai/gpt-image-2/text-to-image"
    normalized_size = _normalize_size(size)
    normalized_quality = _normalize_quality(quality)
    payload = {
        "model": model,
        "prompt": normalized_prompt,
        "size": normalized_size,
        "quality": normalized_quality,
    }

    prediction_id = submit_generation_task("generateImage", payload)
    outputs = wait_for_prediction(
        prediction_id,
        timeout_seconds=300,
        poll_interval_seconds=3,
    )
    if not outputs:
        raise FailException("图像生成失败：未返回图像结果")

    result_lines = [
        "✓ 成功生成图片",
        f"模型: {model}",
        f"尺寸: {normalized_size}",
        f"质量: {normalized_quality}",
        "",
    ]

    for idx, image_url in enumerate(outputs, 1):
        persisted_url = persist_remote_image(
            image_url,
            source="atlascloud-gpt-image-2-text-to-image",
        )
        result_lines.append(f"图片 {idx}:")
        result_lines.append(f"  URL: {persisted_url}")
        result_lines.append("")

    return "\n".join(result_lines).rstrip()


@add_attribute("args_schema", AtlasCloudGPTImage2TextToImageArgsSchema)
def atlascloud_gpt_image_2_text_to_image(**kwargs) -> StructuredTool:
    """Atlas Cloud GPT Image 2 文生图工具。"""
    return StructuredTool.from_function(
        name="atlascloud_gpt_image_2_text_to_image",
        description="使用 Atlas Cloud 的 GPT Image 2 生成高质量图像，支持多种输出尺寸与质量档位。",
        func=lambda prompt, size="1024x1024", quality="medium": _generate_image(**{
            **kwargs,
            "prompt": prompt,
            "size": size,
            "quality": quality,
        }),
        args_schema=AtlasCloudGPTImage2TextToImageArgsSchema,
    )
