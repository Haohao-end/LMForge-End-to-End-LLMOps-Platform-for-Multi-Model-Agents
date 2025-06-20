from typing import Any
from pydantic import BaseModel, Field
from internal.entity.app_entity import DEFAULT_APP_CONFIG


class BuiltinAppEntity(BaseModel):
    """内置工具实体类"""
    id: str = Field(default="")
    category: str = Field(default="")
    name: str = Field(default="")
    icon: str = Field(default="")
    description: str = Field(default="")
    language_model_config: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("model_config"))
    dialog_round: int = Field(default=DEFAULT_APP_CONFIG.get("dialog_round"))
    preset_prompt: str = Field(default=DEFAULT_APP_CONFIG.get("preset_prompt"))
    tools: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_config: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("retrieval_config"))
    long_term_memory: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("long_term_memory"))
    opening_statement: str = Field(default=DEFAULT_APP_CONFIG.get("opening_statement"))
    opening_questions: list[str] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("opening_questions"))
    speech_to_text: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("speech_to_text"))
    text_to_speech: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("text_to_speech"))
    suggested_after_answer: dict[str, Any] = Field(
        default_factory=lambda: DEFAULT_APP_CONFIG.get("suggested_after_answer"),
    )
    review_config: dict[str, Any] = Field(default_factory=lambda: DEFAULT_APP_CONFIG.get("review_config"))
    created_at: int = Field(default=0)
