from __future__ import annotations

from marshmallow import Schema, fields, pre_dump
from wtforms import StringField
from wtforms.validators import Length, Optional

from internal.lib.helper import datetime_to_timestamp
from pkg.paginator import PaginatorReq


class GetSkillsWithPageReq(PaginatorReq):
    """获取技能包分页列表请求。"""

    search_word = StringField("search_word", default="", validators=[Optional()])
    category = StringField("category", default="", validators=[Optional(), Length(max=64)])


class SkillToolInputResp(Schema):
    name = fields.String()
    type = fields.String()
    required = fields.Boolean()
    description = fields.String()


class SkillToolResp(Schema):
    name = fields.String()
    label = fields.String()
    description = fields.String()
    entrypoint = fields.String()
    inputs = fields.List(fields.Nested(SkillToolInputResp), dump_default=[])


class SkillPackageResp(Schema):
    id = fields.UUID(dump_default="")
    source_key = fields.String(dump_default="")
    name = fields.String(dump_default="")
    label = fields.String(dump_default="")
    icon = fields.String(dump_default="")
    description = fields.String(dump_default="")
    readme = fields.String(dump_default="")
    category = fields.String(dump_default="")
    tags = fields.List(fields.String(), dump_default=[])
    capabilities = fields.Dict(dump_default={})
    executor_type = fields.String(dump_default="scf")
    tool_count = fields.Integer(dump_default=0)
    tools = fields.List(fields.Nested(SkillToolResp), dump_default=[])
    created_at = fields.Integer(dump_default=0)
    updated_at = fields.Integer(dump_default=0)

    @pre_dump
    def process_data(self, data, **kwargs):
        if isinstance(data, dict):
            return data
        return {
            "id": data.id,
            "source_key": data.source_key,
            "name": data.name,
            "label": data.label,
            "icon": data.icon,
            "description": data.description,
            "readme": getattr(data, "readme", ""),
            "category": data.category,
            "tags": data.tags or [],
            "capabilities": data.capabilities or {},
            "executor_type": data.executor_type,
            "tool_count": getattr(data, "tool_count", 0),
            "tools": getattr(data, "tools", []),
            "created_at": datetime_to_timestamp(data.created_at),
            "updated_at": datetime_to_timestamp(data.updated_at),
        }


class GetSkillsCategoriesResp(Schema):
    categories = fields.List(fields.Dict())

    class Meta:
        strict = True

    def dump(self, obj, **kwargs):
        return {"categories": obj.get("categories", []) if isinstance(obj, dict) else []}
