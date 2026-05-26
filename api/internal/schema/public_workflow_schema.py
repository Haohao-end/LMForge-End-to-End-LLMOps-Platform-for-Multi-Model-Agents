"""公共工作流Schema"""
from flask_wtf import FlaskForm
from marshmallow import Schema, fields
from wtforms import StringField
from wtforms.validators import Length, Optional

from pkg.paginator import PaginatorReq


class ShareWorkflowToSquareReq(FlaskForm):
    """共享工作流到广场请求"""
    tags = StringField(
        "tags",
        validators=[Optional(), Length(max=500)]
    )


class GetPublicWorkflowsWithPageReq(PaginatorReq):
    """获取公共工作流列表请求"""
    tags = StringField("tags", default="", validators=[Optional()])
    search_word = StringField("search_word", default="", validators=[Optional()])


class PublicWorkflowResp(Schema):
    """公共工作流响应"""
    id = fields.String()
    name = fields.String()
    icon = fields.String()
    description = fields.String()
    tags = fields.List(fields.String())
    published_at = fields.Integer()
    created_at = fields.Integer()
    is_forked = fields.Boolean()  # 是否已fork
    account_name = fields.String()  # 新增发布者名称
    account_avatar = fields.String()  # 新增发布者头像


class ForkWorkflowResp(Schema):
    """Fork工作流响应"""
    id = fields.String()
    name = fields.String()
