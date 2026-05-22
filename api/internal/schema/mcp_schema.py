from __future__ import annotations

from flask_wtf import FlaskForm
from marshmallow import Schema, fields
from wtforms import BooleanField, IntegerField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL, ValidationError

from internal.entity.mcp_entity import MCP_CATEGORY_OPTIONS
from internal.schema import DictField, ListField
from pkg.paginator import PaginatorReq


_SUPPORTED_TRANSPORTS = {"http", "sse", "streamable_http", "streamable-http", "stdio"}


class GetMcpProvidersWithPageReq(PaginatorReq):
    """获取 MCP 列表请求。"""

    search_word = StringField("search_word", default="", validators=[Optional()])
    category = StringField("category", default="", validators=[Optional(), Length(max=64)])


class CreateMcpProviderReq(FlaskForm):
    """创建 MCP 提供者请求。"""

    name = StringField(
        "name",
        validators=[
            DataRequired("MCP 名称不能为空"),
            Length(max=255, message="MCP 名称长度不能超过255个字符"),
        ],
    )
    label = StringField(
        "label",
        validators=[
            Optional(),
            Length(max=255, message="MCP 标题长度不能超过255个字符"),
        ],
    )
    icon = StringField(
        "icon",
        validators=[
            Optional(),
            URL(message="MCP 图标必须是有效的URL链接"),
        ],
    )
    description = StringField(
        "description",
        validators=[
            DataRequired("MCP 描述不能为空"),
            Length(max=1000, message="MCP 描述长度不能超过1000个字符"),
        ],
    )
    category = StringField("category", default="other", validators=[Optional(), Length(max=64)])
    transport = StringField("transport", default="streamable_http", validators=[Optional()])
    url = StringField("url", default="", validators=[Optional(), Length(max=1024)])
    command = StringField("command", default="", validators=[Optional(), Length(max=1024)])
    headers = ListField("headers", default=[])
    tool_names = ListField("tool_names", default=[])
    args = ListField("args", default=[])
    env = DictField("env", default={})
    timeout_seconds = IntegerField(
        "timeout_seconds",
        default=30,
        validators=[Optional(), NumberRange(min=1, max=600, message="超时时间范围必须在1~600秒之间")],
    )

    def validate_transport(self, field: StringField) -> None:
        normalized = str(field.data or "").strip()
        if not normalized:
            return
        if normalized.lower() not in _SUPPORTED_TRANSPORTS:
            raise ValidationError("transport 仅支持 http、sse、streamable_http 或 stdio")

    def validate_headers(self, field: ListField) -> None:
        if field.data in (None, []):
            return
        if not isinstance(field.data, list):
            raise ValidationError("headers 必须是数组")
        for header in field.data:
            if not isinstance(header, dict):
                raise ValidationError("headers 里的每个元素都必须是对象")
            if set(header.keys()) != {"key", "value"}:
                raise ValidationError("headers 里的每个元素都必须只包含 key 和 value")

    def validate_tool_names(self, field: ListField) -> None:
        if field.data in (None, []):
            return
        if not isinstance(field.data, list):
            raise ValidationError("tool_names 必须是数组")

    def validate_args(self, field: ListField) -> None:
        if field.data in (None, []):
            return
        if not isinstance(field.data, list):
            raise ValidationError("args 必须是数组")

    def validate_env(self, field: DictField) -> None:
        if field.data in (None, {}):
            return
        if not isinstance(field.data, dict):
            raise ValidationError("env 必须是对象")


class UpdateMcpProviderReq(CreateMcpProviderReq):
    """更新 MCP 提供者请求。"""


class McpCategoryResp(Schema):
    id = fields.String()
    name = fields.String()
    priority = fields.Integer()
    background = fields.String()


class McpToolInputResp(Schema):
    name = fields.String()
    type = fields.String()
    required = fields.Boolean()
    description = fields.String()


class McpToolResp(Schema):
    name = fields.String()
    label = fields.String()
    description = fields.String()
    inputs = fields.List(fields.Nested(McpToolInputResp), dump_default=[])


class McpProviderResp(Schema):
    id = fields.String()
    provider_key = fields.String()
    name = fields.String()
    label = fields.String()
    icon = fields.String()
    background = fields.String()
    description = fields.String()
    category = fields.String()
    transport = fields.String()
    url = fields.String()
    command = fields.String()
    headers = fields.List(fields.Dict(), dump_default=[])
    tool_names = fields.List(fields.String(), dump_default=[])
    args = fields.List(fields.String(), dump_default=[])
    env = fields.Dict(dump_default={})
    timeout_seconds = fields.Integer()
    source_type = fields.String()
    source_key = fields.String()
    source_url = fields.String()
    creator_name = fields.String()
    creator_avatar = fields.String()
    is_public = fields.Boolean()
    is_bindable = fields.Boolean()
    bind_reason = fields.String()
    published_at = fields.Integer()
    created_at = fields.Integer()
    updated_at = fields.Integer()
    tool_count = fields.Integer()
    tools = fields.List(fields.Nested(McpToolResp), dump_default=[])
    binding = fields.Dict(dump_default={})


class GetMcpCategoriesResp(Schema):
    categories = fields.List(fields.Nested(McpCategoryResp))

    class Meta:
        strict = True

    def dump(self, obj, **kwargs):
        return {"categories": MCP_CATEGORY_OPTIONS}

