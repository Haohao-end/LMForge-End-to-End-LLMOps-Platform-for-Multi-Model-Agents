from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from internal.exception import FailException
from internal.lib.helper import add_attribute

from ..atlascloud_shared import (
    parse_url_list,
    persist_remote_image,
    submit_generation_task,
    wait_for_prediction,
)


class AtlasCloudGPTImage2EditArgsSchema(BaseModel):
    """Atlas Cloud GPT Image 2 图像编辑参数。"""

    prompt: str = Field(description="用于编辑图片的文本提示(prompt)")
    images: str = Field(description="参考图片URL，多个URL可用逗号或换行分隔")
    size: str = Field(default="1024x1024", description="输出图片尺寸")
    quality: str = Field(default="medium", description="输出图片质量")
    input_fidelity: bool = Field(default=False, description="是否尽量保留输入图片细节")


def _normalize_size(size: str) -> str:
    allowed_sizes = {"1024x1024", "1024x1536", "1536x1024"}
    normalized = str(size or "").strip()
    return normalized if normalized in allowed_sizes else "1024x1024"


def _normalize_quality(quality: str) -> str:
    allowed_qualities = {"low", "medium", "high"}
    normalized = str(quality or "").strip().lower()
    return normalized if normalized in allowed_qualities else "medium"


def _edit_image(
    prompt: str,
    images: str,
    size: str = "1024x1024",
    quality: str = "medium",
    input_fidelity: bool = False,
    **kwargs,
) -> str:
    """使用 Atlas Cloud GPT Image 2 编辑图像。"""
    normalized_prompt = str(prompt or "").strip()
    if not normalized_prompt:
        raise FailException("图像编辑失败：prompt 不能为空")

    image_urls = parse_url_list(images)
    if not image_urls:
        raise FailException("图像编辑失败：至少需要一张参考图片")

    model = "openai/gpt-image-2/edit"
    normalized_size = _normalize_size(size)
    normalized_quality = _normalize_quality(quality)
    payload = {
        "model": model,
        "prompt": normalized_prompt,
        "images": image_urls,
        "size": normalized_size,
        "quality": normalized_quality,
        "input_fidelity": bool(input_fidelity),
    }

    prediction_id = submit_generation_task("generateImage", payload)
    outputs = wait_for_prediction(
        prediction_id,
        timeout_seconds=300,
        poll_interval_seconds=3,
    )
    if not outputs:
        raise FailException("图像编辑失败：未返回图像结果")

    result_lines = [
        "✓ 成功编辑图片",
        f"模型: {model}",
        f"尺寸: {normalized_size}",
        f"质量: {normalized_quality}",
        f"保留细节: {'是' if bool(input_fidelity) else '否'}",
        "",
    ]

    for idx, image_url in enumerate(outputs, 1):
        persisted_url = persist_remote_image(
            image_url,
            source="atlascloud-gpt-image-2-edit",
        )
        result_lines.append(f"结果图片 {idx}:")
        result_lines.append(f"  URL: {persisted_url}")
        result_lines.append("")

    return "\n".join(result_lines).rstrip()


@add_attribute("args_schema", AtlasCloudGPTImage2EditArgsSchema)
def atlascloud_gpt_image_2_edit(**kwargs) -> StructuredTool:
    """Atlas Cloud GPT Image 2 图像编辑工具。"""
    return StructuredTool.from_function(
        name="atlascloud_gpt_image_2_edit",
        description="使用 Atlas Cloud 的 GPT Image 2 对输入图片进行自然语言编辑，支持多参考图输入。",
        func=lambda prompt, images, size="1024x1024", quality="medium", input_fidelity=False: _edit_image(**{
            **kwargs,
            "prompt": prompt,
            "images": images,
            "size": size,
            "quality": quality,
            "input_fidelity": input_fidelity,
        }),
        args_schema=AtlasCloudGPTImage2EditArgsSchema,
    )
